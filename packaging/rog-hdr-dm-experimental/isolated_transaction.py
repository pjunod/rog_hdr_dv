#!/usr/bin/env python3
"""Install/remove ONLY in an explicitly marked, task-owned PRoot Ubuntu root.

No host dpkg calls that mutate state, no display/boot/session/profile operation.
This is downstream package qualification tooling, not an execution receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess

P = 'rog-hdr-dm-experimental'
VERSION = '0.1.0~abi368.1-0ubuntu26.10.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('action', choices=('install', 'rollback'))
    a.add_argument('--root', required=True, type=Path)
    a.add_argument('--evidence', required=True, type=Path, help='new durable evidence directory outside root')
    a.add_argument('--deb', type=Path)
    args = a.parse_args()
    root = args.root.resolve(strict=True)
    evidence = args.evidence.resolve()
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64' or
            not root.is_relative_to('/work') or root == Path('/work') or
            root.is_relative_to('/work/hdr-nativehdr10-20261011/t_bb5b2ce0')):
        raise ValueError('new task-owned native /work PRoot required; no host/historical root')
    marker = root / 'ISOLATED-ABI368-ROOT.json'
    identity = json.loads(marker.read_text())
    if identity != {'schema': 'hdr.abi368.isolated-root.v1', 'purpose': 'package-qualification-only',
                    'package': P, 'version': VERSION}:
        raise ValueError('explicit isolated root marker required')
    if evidence.is_relative_to(root) or not evidence.is_relative_to('/work'):
        raise ValueError('separate durable /work evidence required')
    evidence.mkdir(parents=True, exist_ok=False)
    host_status = Path('/var/lib/dpkg/status')
    host_before = sha(host_status)
    proot = shutil.which('proot')
    if not proot:
        raise ValueError('PRoot prerequisite absent')
    command = [proot, '-0', '-r', str(root), '-w', '/', '/usr/bin/env', '-i',
               'PATH=/usr/sbin:/usr/bin:/sbin:/bin', 'HOME=/root', 'LANG=C', 'LC_ALL=C',
               'TMPDIR=/var/lib/rog-hdr-dm-experimental-scratch']
    (root / 'var/lib/rog-hdr-dm-experimental-scratch').mkdir(parents=True, exist_ok=True)
    query = subprocess.run(command + ['dpkg-query', '-W', '-f=${Status} ${Version}', P],
                           capture_output=True, text=True)
    if args.action == 'install':
        if query.returncode == 0 and query.stdout.startswith('install ok installed'):
            raise ValueError('unique experimental package already installed: refuse overwrite')
        if not args.deb:
            raise ValueError('--deb required for install')
        deb = args.deb.resolve(strict=True)
        fields = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Package', 'Version', 'Architecture'], text=True)
        if fields.splitlines() != ['Package: ' + P, 'Version: ' + VERSION, 'Architecture: amd64']:
            raise ValueError('wrong package artifact identity')
        inside = root / 'var/lib/rog-hdr-dm-experimental-install.deb'
        if inside.exists():
            raise ValueError('root artifact already present')
        shutil.copy2(deb, inside)
        operation = ['dpkg', '-i', '/var/lib/rog-hdr-dm-experimental-install.deb']
        artifact_sha = sha(deb)
    else:
        if query.returncode or query.stdout != 'install ok installed ' + VERSION:
            raise ValueError('exact installed experimental package required for rollback')
        operation = ['dpkg', '--purge', P]
        artifact_sha = None
    with (evidence / 'transaction.stdout').open('xb') as out, (evidence / 'transaction.stderr').open('xb') as err:
        result = subprocess.run(command + operation, stdout=out, stderr=err, timeout=180)
    after = subprocess.run(command + ['dpkg-query', '-W', '-f=${Status} ${Version}', P], capture_output=True, text=True)
    success = (result.returncode == 0 and host_before == sha(host_status) and
               (after.returncode == 0 and after.stdout == 'install ok installed ' + VERSION
                if args.action == 'install' else after.returncode != 0))
    receipt = {'schema': 'hdr.abi368.isolated-transaction.v1', 'action': args.action,
               'root': str(root), 'root_marker_sha256': sha(marker), 'artifact_sha256': artifact_sha,
               'command': command + operation, 'exit': result.returncode,
               'query_before': {'exit': query.returncode, 'stdout': query.stdout},
               'query_after': {'exit': after.returncode, 'stdout': after.stdout},
               'host_dpkg_before_sha256': host_before, 'host_dpkg_after_sha256': sha(host_status),
               'stdout_sha256': sha(evidence / 'transaction.stdout'),
               'stderr_sha256': sha(evidence / 'transaction.stderr'), 'pass': success,
               'scope': 'private PRoot package transaction only, no physical deployment'}
    (evidence / 'TRANSACTION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if not success:
        raise ValueError('isolated transaction failed; inspect retained evidence')
    print(evidence / 'TRANSACTION.json')


if __name__ == '__main__':
    main()
