#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prepare pinned Ubuntu source; no download, compilation or installation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('webkit_verify', HERE / 'verify-build.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def run(command, source, **kwargs):
    subprocess.run(command, cwd=source, check=True, **kwargs)


def verify_quilt(path, series):
    if path.is_symlink() or not path.is_dir():
        raise verify.VerificationError('quilt metadata root must be an owned regular directory')
    for child in path.rglob('*'):
        mode = child.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise verify.VerificationError('quilt metadata contains a symlink or special file')
    if (path / 'applied-patches').read_text().splitlines() != series:
        raise verify.VerificationError('quilt state does not match the original Ubuntu series')


def validate_recorded_patch(body, expected_paths):
    if any(token in body for token in ('GIT binary patch', 'Binary files ', 'rename from ', 'rename to ')):
        raise verify.VerificationError('recorded patch is not a regular text-only product delta')
    touched = set()
    headers = []
    for line in body.splitlines():
        if not line.startswith(('--- ', '+++ ')):
            continue
        value = line[4:].split('\t', 1)[0].split(' ', 1)[0]
        if value == '/dev/null':
            headers.append(None)
            continue
        path = Path(value)
        if path.is_absolute() or '..' in path.parts or len(path.parts) < 2:
            raise verify.VerificationError('unsafe path in recorded product patch')
        name = '/'.join(path.parts[1:])
        if name not in expected_paths:
            raise verify.VerificationError('unexpected file in recorded product patch: ' + name)
        touched.add(name)
        headers.append(name)
    if touched != set(expected_paths) or len(headers) != 2 * len(expected_paths):
        raise verify.VerificationError('recorded patch does not contain exactly the reviewed product paths')
    for old, new in zip(headers[::2], headers[1::2]):
        if new is None or (old is not None and old != new):
            raise verify.VerificationError('recorded patch removes or renames a product file')


def source_mtimes(source):
    result = {}
    for name in ('CMakeLists.txt', 'NEWS', 'Documentation', 'Source', 'Tools'):
        path = source / name
        files = path.rglob('*') if path.is_dir() else [path]
        for child in files:
            if child.is_file() and '__pycache__' not in child.parts and child.suffix != '.pyc':
                result[str(child.relative_to(source))] = child.lstat().st_mtime_ns
    return result


def prepare(source, patch, already_patched=False, quilt_state_from=None):
    source = source.resolve()
    pin = json.loads((HERE / 'source-pin.json').read_text())
    if hashlib.sha256(patch.read_bytes()).hexdigest() != pin['product_patch_sha256']:
        raise verify.VerificationError('product patch differs from reviewed source pin')
    original = source.parent / 'webkit2gtk_2.52.6.orig.tar.xz'
    expected = pin['ubuntu_source_archives'][original.name]
    if not original.is_file():
        raise verify.VerificationError('keep the authenticated webkit2gtk_2.52.6.orig.tar.xz next to the source')
    if original.stat().st_size != expected['size'] or hashlib.sha256(original.read_bytes()).hexdigest() != expected['sha256']:
        raise verify.VerificationError('original source archive differs from the Ubuntu descriptor')
    if (source / 'debian/rog-native-hdr').exists():
        raise verify.VerificationError('source already prepared; use a fresh source extraction')
    # The original Debian files must be exact in either mode. Product code can
    # already be present in the active warm source: do not rewrite its mtimes.
    phase = 'candidate' if already_patched else 'base'
    verify.verify_source(source, pin, phase, packaging=True)
    if verify.object_id(source / 'debian', ignore_python=False) != pin['base']['debian']:
        raise verify.VerificationError('Ubuntu debian/ differs from source pin')
    series = [line.split()[0] for line in (source / 'debian/patches/series').read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    if (source / '.pc').is_symlink():
        raise verify.VerificationError('quilt metadata root is a symlink')
    if not (source / '.pc').exists():
        if quilt_state_from is None:
            raise verify.VerificationError('missing Ubuntu quilt state; supply --quilt-state-from a clean authenticated extraction')
        baseline = quilt_state_from.resolve()
        verify.verify_source(baseline, pin, 'base', packaging=True)
        verify_quilt(baseline / '.pc', series)
        shutil.copytree(baseline / '.pc', source / '.pc')
    verify_quilt(source / '.pc', series)
    if not already_patched:
        run(['patch', '--batch', '--forward', '-p1', '-i', str(patch.resolve())], source)
    verify.verify_source(source, pin)
    # dpkg-source records the existing product delta in the ordinary quilt
    # series and .pc state. This supports both a freshly patched extraction
    # and the identical source that produced a retained external object cache.
    mtimes = source_mtimes(source)
    env = dict(os.environ, EDITOR='true', VISUAL='true')
    ignore = r'(^|/)(__pycache__(/|$)|[^/]+[.]pyc$|build-gtk4(/|$))'
    run(['dpkg-source', '--extend-diff-ignore=' + ignore, '--commit', '.', 'rog-native-hdr.patch'], source, env=env)
    if source_mtimes(source) != mtimes:
        raise verify.VerificationError('dpkg-source changed a product source mtime; retain this failed preparation')
    recorded = source / 'debian/patches/rog-native-hdr.patch'
    body = recorded.read_text()
    validate_recorded_patch(body, pin['product_paths'])
    marker = body.find('\n--- ')
    if marker < 0:
        raise verify.VerificationError('dpkg-source did not record a source patch')
    recorded.write_text('Description: Clear-video destination and native GTK HDR plane\n'
                        'Origin: other, reviewed source ' + pin['candidate_commit'] + '\n'
                        'Forwarded: no\nLast-Update: 2026-11-09\n' + body[marker:])
    verify.verify_source(source, pin)
    run(['patch', '--batch', '--forward', '-p1', '-i', str(HERE / 'ubuntu-packaging.diff')], source)
    (source / 'debian/source/options').write_text(
        'extend-diff-ignore = "' + ignore + '"\n'
        'tar-ignore = "__pycache__"\n'
        'tar-ignore = "*.pyc"\n')
    target = source / 'debian/rog-native-hdr'
    target.mkdir()
    for name in ('verify-build.py', 'source-pin.json', 'cmake-profile.json', 'cmake-features.json'):
        shutil.copy2(HERE / name, target / name)
    old = source / 'debian/changelog'
    old.write_text('webkit2gtk (' + pin['package_version'] + ') stonking; urgency=medium\n\n'
                   '  * Build reviewed clear-video/native HDR source as GTK4-only packages.\n'
                   '  * Preserve distribution debhelper, symbols and generated dependencies.\n\n'
                   ' -- ROG HDR contributors <rog-hdr@example.invalid>  Mon, 09 Nov 2026 00:00:00 +0000\n\n'
                   + old.read_text())
    run(['make', '-f', 'debian/rules', 'debian/control'], source)
    names = [line.split(': ', 1)[1] for line in (source / 'debian/control').read_text().splitlines()
             if line.startswith('Package: ')]
    if names != pin['binary_packages']:
        raise verify.VerificationError(f'unexpected generated package inventory: {names}')
    print('Prepared six GTK4 packages. No compiler, cache cleanup or installation was run.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--product-patch', required=True, type=Path)
    parser.add_argument('--already-patched', action='store_true')
    parser.add_argument('--quilt-state-from', type=Path,
                        help='clean authenticated Ubuntu extraction; restores absent .pc metadata only')
    args = parser.parse_args()
    prepare(args.source, args.product_patch, args.already_patched, args.quilt_state_from)


if __name__ == '__main__':
    try:
        main()
    except (verify.VerificationError, subprocess.CalledProcessError, OSError, ValueError) as error:
        sys.exit(f'WebKit source preparation refused: {error}')
