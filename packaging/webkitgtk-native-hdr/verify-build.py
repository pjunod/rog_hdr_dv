#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fail closed before reusing objects; never configure, compile or delete files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


class VerificationError(Exception):
    pass


def git_object(kind, data):
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def object_id(path):
    """Reproduce Git trees without a Git checkout, including executable modes."""
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return git_object('blob', os.fsencode(os.readlink(path)))
    if stat.S_ISREG(mode):
        return git_object('blob', path.read_bytes())
    if not stat.S_ISDIR(mode):
        raise VerificationError(f'unsupported source file: {path}')
    entries = []
    for child in path.iterdir():
        # Python's generated cache is never a source input in this distribution.
        if child.name == '__pycache__' or child.name.endswith('.pyc'):
            continue
        child_mode = child.lstat().st_mode
        directory = stat.S_ISDIR(child_mode)
        git_mode = ('40000' if directory else '120000' if stat.S_ISLNK(child_mode)
                    else '100755' if child_mode & 0o111 else '100644')
        name = os.fsencode(child.name)
        entries.append((name + (b'/' if directory else b''),
                        git_mode.encode() + b' ' + name + b'\0' + bytes.fromhex(object_id(child))))
    return git_object('tree', b''.join(value for _, value in sorted(entries)))


def verify_source(source, pin, phase='candidate', packaging=False):
    expected_names = set(pin['common']) | {'Source', 'Tools', 'debian'}
    allowed_metadata = {'.pc', '.git'}
    if not packaging:
        allowed_metadata.add('build-gtk4')
    unknown = {path.name for path in source.iterdir()} - expected_names - allowed_metadata
    if unknown:
        raise VerificationError('unexpected top-level source input: ' + ', '.join(sorted(unknown)))
    expected = dict(pin['common'], **pin[phase])
    if not packaging:
        expected.pop('debian', None)
    for name, expected_id in expected.items():
        if object_id(source / name) != expected_id:
            raise VerificationError(f'{name}: source differs from pinned {phase}')


def read_cache(path):
    values = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith(('#', '//')) or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.split(':', 1)[0]
        if key in values:
            raise VerificationError(f'duplicate CMake cache key: {key}')
        values[key] = value
    return values


def build_path(source, value):
    if any(c.isspace() for c in value):
        raise VerificationError('build directory cannot contain whitespace')
    supplied = Path(value)
    if value != 'build-gtk4' and not supplied.is_absolute():
        raise VerificationError('external build directory must be absolute')
    path = supplied if supplied.is_absolute() else source / supplied
    if path.is_symlink():
        raise VerificationError('build directory must not be a symlink')
    path = path.resolve()
    if path == source or source.is_relative_to(path):
        raise VerificationError('build directory cannot contain the source')
    if value != 'build-gtk4' and path.is_relative_to(source):
        raise VerificationError('use build-gtk4 for source-owned builds')
    return path


def verify_cache(source, build, profile):
    cache = read_cache(build / 'CMakeCache.txt')
    feature_file = Path(__file__).with_name('cmake-features.json')
    feature_receipt = json.loads(feature_file.read_text())
    wanted_features = feature_receipt['feature_map']
    canonical = json.dumps(wanted_features, sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(canonical).hexdigest() != feature_receipt['feature_map_sha256']:
        raise VerificationError('feature profile fingerprint is inconsistent')
    actual_features = {}
    for line in (build / 'CMakeCache.txt').read_text().splitlines():
        if '=' not in line or ':BOOL=' not in line:
            continue
        key, value = line.split(':BOOL=', 1)
        if key.startswith(('ENABLE_', 'USE_')):
            actual_features[key] = value
    if actual_features != wanted_features:
        changed = sorted(key for key in set(actual_features) | set(wanted_features)
                         if actual_features.get(key) != wanted_features.get(key))
        raise VerificationError('CMake feature map differs: ' + ', '.join(changed))
    if 'ENABLE_LTO' in cache:
        raise VerificationError('ENABLE_LTO was absent in the reviewed profile')
    expected = dict(profile, CMAKE_HOME_DIRECTORY=str(source), CMAKE_CACHEFILE_DIR=str(build), CMAKE_GENERATOR='Ninja',
                    GTK_DOVI_SDK_ROOT=os.environ.get('ROG_WEBKIT_DOVI_SDK_ROOT', '/usr/include'),
                    GTK_NATIVE_VIDEO_GDK_SDK_ROOT=os.environ.get('ROG_WEBKIT_GDK_SDK_ROOT', '/usr/include/gtk-4.0'))
    for key, wanted in expected.items():
        actual = cache.get(key)
        if actual != wanted:
            raise VerificationError(f'{key}: expected {wanted!r}, found {actual!r}')
    for path in (build / 'build.ninja', build / 'CMakeFiles/rules.ninja'):
        if not path.is_file() or path.is_symlink() or not path.read_bytes().startswith(b'# CMAKE generated file:'):
            raise VerificationError('missing or invalid configured Ninja graph/rules')
    return cache


def sha256_file(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def bound_file(record, expected_path=None):
    if set(record) != {'path', 'sha256'}:
        raise VerificationError('producer file record needs path and sha256')
    path = Path(record['path'])
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise VerificationError('producer reference must be an absolute regular file')
    if expected_path is not None and path != expected_path:
        raise VerificationError('producer reference names a different file')
    if sha256_file(path) != record['sha256']:
        raise VerificationError('producer referenced file identity differs')


def verify_producer(source, build, profile, pin, receipt_path):
    """Validate a local operator's retained producer input, not a CI attestation."""
    if receipt_path is None:
        raise VerificationError('external reuse requires ROG_WEBKIT_REUSE_RECEIPT from the completed guarded producer')
    path = Path(receipt_path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise VerificationError('producer receipt must be an absolute regular file')
    if path.resolve().is_relative_to(source) or path.resolve().is_relative_to(build):
        raise VerificationError('keep the private producer receipt outside source and build')
    receipt = json.loads(path.read_text())
    feature_hash = json.loads(Path(__file__).with_name('cmake-features.json').read_text())['feature_map_sha256']
    expected = {
        'schema': 'rog-webkit-local-producer-v1', 'trust': 'local-operator',
        'source_directory': str(source), 'build_directory': str(build),
        'candidate_commit': pin['candidate_commit'], 'feature_map_sha256': feature_hash,
        'cmake_profile_sha256': hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'completed_guard': True,
        'sdk_compile_checks': {'gdk_native_hdr': True, 'mapper_destination_abi': True, 'mapper_source_lease_abi': True},
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise VerificationError('local producer receipt differs: ' + key)
    file_names = {'cache': build / 'CMakeCache.txt', 'graph': build / 'build.ninja',
                  'rules': build / 'CMakeFiles/rules.ninja'}
    if set(receipt.get('files', {})) != set(file_names):
        raise VerificationError('producer must bind cache, graph and rules')
    for key, file_path in file_names.items():
        bound_file(receipt['files'][key], file_path)
    if set(receipt.get('inputs', {})) != {'guard', 'source_archive', 'sdk_controls'}:
        raise VerificationError('producer must retain guard, source archive and SDK control evidence')
    for record in receipt['inputs'].values():
        bound_file(record)
    headers = {
        'mapper': Path(os.environ.get('ROG_WEBKIT_DOVI_SDK_ROOT', '/usr/include')) / 'gst-gtk-dovi-1.0/mapper.h',
        'gdkwayland': Path(os.environ.get('ROG_WEBKIT_GDK_SDK_ROOT', '/usr/include/gtk-4.0')) / 'gdk/wayland/gdkwaylandsurface.h',
    }
    if set(receipt.get('sdk_headers', {})) != set(headers):
        raise VerificationError('producer must bind both selected native SDK headers')
    for key, header in headers.items():
        bound_file(receipt['sdk_headers'][key], header.resolve())
    commands = subprocess.check_output(['/usr/bin/ninja', '-C', str(build), '-t', 'commands'])
    if not commands.strip() or hashlib.sha256(commands).hexdigest() != receipt.get('ninja_commands_sha256'):
        raise VerificationError('producer Ninja command identity differs')
    print('External reuse matches the retained local operator producer input; this is not CI authentication.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--build-dir', default=os.environ.get('ROG_WEBKIT_BUILD_DIR', 'build-gtk4'))
    parser.add_argument('--path-only', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    build = build_path(source, args.build_dir)
    if args.path_only:
        print(build)
        return
    here = Path(__file__).resolve().parent
    pin = json.loads((here / 'source-pin.json').read_text())
    profile = json.loads((here / 'cmake-profile.json').read_text())
    verify_source(source, pin)
    verify_cache(source, build, profile)
    if args.build_dir != 'build-gtk4':
        verify_producer(source, build, profile, pin, os.environ.get('ROG_WEBKIT_REUSE_RECEIPT'))
    print('Reviewed source and GTK4 distro-path CMake profile match; cache may be reused.')


if __name__ == '__main__':
    try:
        main()
    except (VerificationError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        sys.exit(f'WebKit packaging refused: {error}')
