#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build normal launcher source/binary packages in a fresh native owned directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source-archive', required=True, type=Path,
                        help='git archive <commit>:tools/native_player, prepared before transfer')
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('use the authorized native x86_64 builder')
    output = Path(args.output).resolve()
    if any(output == Path(p) or Path(p) in output.parents
           for p in ('/tmp', '/private/tmp', '/var/tmp')):
        raise ValueError('output must be durable')
    if not re.fullmatch('[0-9a-f]{40}', args.commit):
        raise ValueError('full committed source identity required')
    if not re.fullmatch('[0-9a-f]{64}', args.sha256) or sha(args.source_archive) != args.sha256:
        raise ValueError('committed source archive hash mismatch')
    output.mkdir(parents=True, exist_ok=False)
    archive = output / 'committed-source.tar'
    shutil.copyfile(args.source_archive, archive)
    source = output / 'hermes-hdr-experimental-player'
    source.mkdir()
    with tarfile.open(archive) as packed:
        packed.extractall(source, filter='data')
    scratch = output / 'scratch'
    scratch.mkdir(mode=0o700)
    env = dict(os.environ, TMPDIR=str(scratch), DEB_BUILD_OPTIONS='nocheck', DEB_BUILD_PROFILES='nocheck')
    cmd = ['dpkg-buildpackage', '-F', '-us', '-uc']
    with (output / 'build.log').open('w') as log:
        subprocess.run(cmd, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    artifacts = [p for p in sorted(output.iterdir()) if p.suffix in ('.deb', '.dsc', '.xz', '.changes', '.buildinfo')]
    if {p.suffix for p in artifacts} != {'.deb', '.dsc', '.xz', '.changes', '.buildinfo'}:
        raise ValueError('source/binary artifact closure incomplete')
    receipt = {'schema':2,'status':'constructed-not-installed-not-unit-validated',
               'source_commit':args.commit,'source_archive_sha256':sha(archive),
               'native_architecture':platform.machine(),'command':cmd,
               'artifacts':{p.name:sha(p) for p in artifacts},
               'build_log_sha256':sha(output / 'build.log'),
               'units_run':0,'physical_trials_run':0,'installs':0}
    (output / 'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output / 'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in artifacts))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
