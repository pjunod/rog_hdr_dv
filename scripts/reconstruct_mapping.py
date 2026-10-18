#!/usr/bin/env python3
"""Reconstruct the exact frozen library from public upstream plus original mails.

Only new destinations are accepted. No build, test, install or vendor access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'cee9b076f2c63104ccfd497fa79c39a867293ec4'
SERIES = ('open-xml205/0001-dovi-add-frame-owned-open-L1-mapping-and-explicit-ta.patch',
          'open-xml205/0002-utils-Keep-the-DM-adapter-header-warning-clean-in-C.patch',
          'open-xml205/0003-dovi-add-explicit-OPEN-analytic-PQ-Hermite-and-typed.patch',
          'absolute-pq/0001-absolute-pq-sop.patch',
          'public-rgb/0001-source-grounded-rgb-pq-pre.patch')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def verify(root):
    pin = json.loads((ROOT / 'wip/libplacebo-dm/public-rgb/SOURCE.json').read_text())
    if git(root, 'rev-parse', 'HEAD^{tree}') != pin['identity']['tree']:
        raise ValueError('reconstructed tree differs from frozen numerical candidate')
    for rel, digest in pin['sources'].items():
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen source mismatch: ' + rel)
    return pin


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    args = p.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        raise ValueError('destination must not exist')
    subprocess.run(['git', 'clone', '--no-checkout', 'https://github.com/haasn/libplacebo.git', str(dest)], check=True)
    subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', BASE], check=True)
    git(dest, 'config', 'user.name', 'HDR Engineering')
    git(dest, 'config', 'user.email', 'hdr-engineering@users.noreply.github.com')
    patches = ROOT / 'wip/libplacebo-dm'
    for directory in ('open-xml205', 'absolute-pq', 'public-rgb'):
        for line in (patches / directory / 'SHA256SUMS').read_text().splitlines():
            digest, name = line.split('  ', 1)
            path = patches / directory / name
            if path.parent != patches / directory or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('original patch checksum mismatch')
    subprocess.run(['git', '-C', str(dest), 'am', *[str(patches / name) for name in SERIES]], check=True)
    pin = verify(dest)
    subprocess.run(['git', '-C', str(dest), 'submodule', 'update', '--init', '3rdparty/fast_float'], check=True)
    print(json.dumps({'schema': 'hdr.abi368.reconstruction.v1', 'base': BASE,
                      'tree': pin['identity']['tree'], 'source_files': len(pin['sources']),
                      'replayed_head': git(dest, 'rev-parse', 'HEAD'),
                      'historical_head': pin['identity']['head'],
                      'units_run': 0, 'renders_run': 0}, indent=2))


if __name__ == '__main__':
    main()
