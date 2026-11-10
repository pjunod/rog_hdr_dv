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
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('webkit_verify', HERE / 'verify-build.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def run(command, source, **kwargs):
    subprocess.run(command, cwd=source, check=True, **kwargs)


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
    verify.verify_source(source, pin, phase)
    if verify.object_id(source / 'debian') != pin['base']['debian']:
        raise verify.VerificationError('Ubuntu debian/ differs from source pin')
    if not (source / '.pc/applied-patches').is_file():
        if quilt_state_from is None:
            raise verify.VerificationError('missing Ubuntu quilt state; supply --quilt-state-from a clean authenticated extraction')
        baseline = quilt_state_from.resolve()
        verify.verify_source(baseline, pin, 'base', packaging=True)
        quilt = baseline / '.pc'
        applied = (quilt / 'applied-patches').read_text().splitlines()
        series = [line.split()[0] for line in (baseline / 'debian/patches/series').read_text().splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
        if applied != series or any(path.is_symlink() for path in quilt.rglob('*')):
            raise verify.VerificationError('clean extraction has unexpected or unsafe Ubuntu quilt state')
        if (source / '.pc').exists():
            raise verify.VerificationError('partial .pc state exists; preserve it and use a fresh extraction')
        shutil.copytree(quilt, source / '.pc')
    applied = (source / '.pc/applied-patches').read_text().splitlines()
    series = [line.split()[0] for line in (source / 'debian/patches/series').read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    if applied != series:
        raise verify.VerificationError('source quilt state does not match the original Ubuntu series')
    if not already_patched:
        run(['patch', '--batch', '--forward', '-p1', '-i', str(patch.resolve())], source)
    verify.verify_source(source, pin)
    # dpkg-source records the existing product delta in the ordinary quilt
    # series and .pc state. This supports both a freshly patched extraction
    # and the identical source that produced a retained external object cache.
    env = dict(os.environ, EDITOR='true', VISUAL='true')
    run(['dpkg-source', '--commit', '.', 'rog-native-hdr.patch'], source, env=env)
    recorded = source / 'debian/patches/rog-native-hdr.patch'
    body = recorded.read_text()
    marker = body.find('\n--- ')
    if marker < 0:
        raise verify.VerificationError('dpkg-source did not record a source patch')
    recorded.write_text('Description: Clear-video destination and native GTK HDR plane\n'
                        'Origin: other, reviewed source ' + pin['candidate_commit'] + '\n'
                        'Forwarded: no\nLast-Update: 2026-11-09\n' + body[marker:])
    verify.verify_source(source, pin)
    run(['patch', '--batch', '--forward', '-p1', '-i', str(HERE / 'ubuntu-packaging.diff')], source)
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
