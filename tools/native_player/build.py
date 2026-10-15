#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Construct the launcher .deb in a new native owned directory; never install."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import py_compile
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--epoch', required=True, type=int)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('use the authorized native x86_64 builder')
    output = Path(args.output).resolve()
    if any(output == Path(p) or Path(p) in output.parents
           for p in ('/tmp', '/private/tmp', '/var/tmp')):
        raise ValueError('output must be durable')
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent
    stage = output / 'stage'
    files = {'control': 'DEBIAN/control',
             'player.py': 'usr/bin/hermes-hdr-player',
             'player.desktop': 'usr/share/applications/hermes-hdr-player.desktop',
             'USAGE.txt': 'usr/share/doc/hermes-hdr-experimental-player/USAGE.txt',
             'copyright': 'usr/share/doc/hermes-hdr-experimental-player/copyright',
             'inputs.json': 'usr/share/doc/hermes-hdr-experimental-player/inputs.json'}
    for source, destination in files.items():
        target = stage / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / source, target)
        target.chmod(0o755 if source == 'player.py' else 0o644)
    for path in stage.rglob('*'):
        if path.is_dir():
            path.chmod(0o755)
    stage.chmod(0o755)
    py_compile.compile(str(stage / 'usr/bin/hermes-hdr-player'),
                       cfile=str(output / 'launcher.pyc'), doraise=True)
    package = output / 'hermes-hdr-experimental-player_1.0~experimental2_all.deb'
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(args.epoch))
    cmd = ['dpkg-deb', '--root-owner-group', '--build', str(stage), str(package)]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    metadata = subprocess.check_output(['dpkg-deb', '--info', str(package)], text=True)
    contents = subprocess.check_output(['dpkg-deb', '--contents', str(package)], text=True)
    receipt = {'schema':1,'status':'constructed-not-installed-not-unit-validated',
               'native_architecture':platform.machine(),'epoch':args.epoch,
               'sources':{p.name:sha(p) for p in sorted(root.iterdir()) if p.is_file()},
               'payload':{v:sha(stage / v) for v in files.values()},
               'package':package.name,'package_sha256':sha(package),
               'package_bytes':package.stat().st_size,'command':cmd,
               'stdout':result.stdout,'metadata':metadata,'contents':contents,
               'python_version':platform.python_version(),
               'dpkg_deb_version':subprocess.check_output(['dpkg-deb','--version'],text=True),
               'units_run':0,'physical_trials_run':0,'installs':0}
    (output / 'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output / 'SHA256SUMS').write_text(sha(package)+'  '+package.name+'\n')
    print(json.dumps({'package':str(package),'sha256':sha(package),'units_run':0}))


if __name__ == '__main__':
    main()
