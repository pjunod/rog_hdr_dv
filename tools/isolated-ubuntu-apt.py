#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare and exercise a task-private PRoot APT/dpkg root, never the host.

PRoot is a compatibility mechanism, not a security sandbox. Only trusted Ubuntu
packages enter this root. No host /run, home, credentials, display or service
sockets are bound. A policy-rc.d prevents service activation. Preparation copies
an installed compiler baseline; actual subsequent APT/dpkg transactions must be
reported separately from this copy and from solver simulation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def durable(path):
    path = Path(path).resolve()
    if any(path == Path(p) or Path(p) in path.parents for p in ('/tmp', '/private/tmp', '/var/tmp')):
        raise ValueError('durable root required')
    return path


def host_state():
    return {p: sha(p) for p in ['/var/lib/dpkg/status', '/var/lib/dpkg/arch'] if Path(p).exists()}


def prepare(root):
    if root.exists():
        raise ValueError('fresh owned root required, never reset a live root')
    root.mkdir(parents=True)
    # Fully independent writable payload, no hardlinks to the compiler's /usr.
    shutil.copytree('/usr', root / 'usr', symlinks=True)
    shutil.copytree('/var/lib/dpkg', root / 'var/lib/dpkg', symlinks=True,
                    ignore=shutil.ignore_patterns('lock', 'lock-frontend', 'Lock'))
    for directory in ['dev', 'proc', 'run', 'root', 'scratch', 'kit',
                      'etc/apt/sources.list.d', 'var/lib/apt/lists/partial',
                      'var/cache/apt/archives/partial', 'var/log/apt']:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for path in ['bin', 'sbin', 'lib', 'lib64']:
        (root / path).symlink_to('usr/' + path)
    # Explicit public/configuration allowlist: never copy /etc wholesale.
    for path in ['ld.so.conf', 'ld.so.cache', 'debian_version', 'os-release']:
        source = Path('/etc') / path
        if source.is_file():
            shutil.copyfile(source, root / 'etc' / path)
    if Path('/etc/ld.so.conf.d').is_dir():
        shutil.copytree('/etc/ld.so.conf.d', root / 'etc/ld.so.conf.d', symlinks=True)
    shutil.copytree('/etc/alternatives', root / 'etc/alternatives', symlinks=True)
    (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\n_apt:x:100:65534:APT:/nonexistent:/usr/sbin/nologin\n')
    (root / 'etc/group').write_text('root:x:0:\nnogroup:x:65534:\n')
    policy = root / 'usr/sbin/policy-rc.d'
    if policy.is_symlink():
        policy.unlink()
    policy.write_text('#!/bin/sh\nexit 101\n')
    policy.chmod(0o755)
    # Reuse public package indexes only; exclude root-owned partial/lock entries.
    for path in Path('/var/lib/apt/lists').iterdir():
        if path.is_file() and path.name != 'lock':
            shutil.copyfile(path, root / 'var/lib/apt/lists' / path.name)
    # No sources: validation consumes only the explicit local kit and cache.
    (root / 'etc/apt/sources.list').write_text('')
    (root / 'PREPARED.json').write_text(json.dumps({
        'baseline': 'copied compiler /usr plus actual dpkg database, not a new package installation',
        'host': host_state(), 'credentials_copied': False, 'service_policy': 'exit101',
        'payload_copy': 'independent bytes, no host hardlinks', 'sources': 'offline local packages only'}, indent=2) + '\n')


def command(root, proot, argv):
    if not (root / 'PREPARED.json').is_file():
        raise ValueError('prepared root receipt missing')
    proot = proot.resolve()
    if not proot.is_file():
        raise ValueError('task-private PRoot executable missing')
    env = dict(os.environ, PROOT_NO_SECCOMP='1', PROOT_TMP_DIR=str(root / 'scratch'),
               TMPDIR='/scratch', HOME='/root', LC_ALL='C', DEBIAN_FRONTEND='noninteractive',
               PATH='/usr/sbin:/usr/bin:/sbin:/bin',
               LD_LIBRARY_PATH=str(proot.parents[1] / 'lib/x86_64-linux-gnu'))
    # No /proc host bind, no /dev as a whole, no arbitrary external command cwd.
    return subprocess.run([str(proot), '-0', '-r', str(root), '-w', '/',
                           '-b', '/dev/null', '-b', '/dev/urandom',
                           '/usr/bin/env', '-u', 'LD_LIBRARY_PATH', *argv], env=env,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    prepare_parser = actions.add_parser('prepare')
    prepare_parser.add_argument('--root', required=True, type=Path)
    run_parser = actions.add_parser('run')
    run_parser.add_argument('--root', required=True, type=Path)
    run_parser.add_argument('--proot', required=True, type=Path)
    run_parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or os.geteuid() == 0:
        raise ValueError('unprivileged native x86_64 builder required')
    root = durable(args.root)
    before = host_state()
    if args.action == 'prepare':
        prepare(root)
    else:
        if args.proot is None or not args.command:
            parser.error('run requires --proot and a command following --')
        argv = args.command[1:] if args.command[0] == '--' else args.command
        result = command(root, args.proot, argv)
        print(result.stdout)
        if host_state() != before:
            raise ValueError('host package state changed')
        raise SystemExit(result.returncode)
    if host_state() != before:
        raise ValueError('host package state changed')
    print('PREPARED ONLY; no installation. Host package state unchanged.')


if __name__ == '__main__':
    main()
