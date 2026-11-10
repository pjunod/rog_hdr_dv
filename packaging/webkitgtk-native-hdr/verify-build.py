#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fail closed before reusing objects; never configure, compile or delete files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
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
    expected = dict(profile, CMAKE_HOME_DIRECTORY=str(source), CMAKE_GENERATOR='Ninja',
                    GTK_DOVI_SDK_ROOT=os.environ.get('ROG_WEBKIT_DOVI_SDK_ROOT', '/usr/include'),
                    GTK_NATIVE_VIDEO_GDK_SDK_ROOT=os.environ.get('ROG_WEBKIT_GDK_SDK_ROOT', '/usr/include/gtk-4.0'))
    for key, wanted in expected.items():
        actual = cache.get(key)
        if actual != wanted:
            raise VerificationError(f'{key}: expected {wanted!r}, found {actual!r}')
    if not (build / 'build.ninja').is_file():
        raise VerificationError('missing configured Ninja graph')
    return cache


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
    verify_source(source, json.loads((here / 'source-pin.json').read_text()))
    verify_cache(source, build, json.loads((here / 'cmake-profile.json').read_text()))
    print('Reviewed source and GTK4 distro-path CMake profile match; cache may be reused.')


if __name__ == '__main__':
    try:
        main()
    except (VerificationError, OSError, ValueError) as error:
        sys.exit(f'WebKit packaging refused: {error}')
