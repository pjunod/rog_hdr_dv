#!/usr/bin/env python3
"""Prepare a complete source-package tree from a verified public reconstruction.

Does not build packages, install, test, or copy a live checkout wholesale.
The library argument must have pinned fast_float submodule initialized.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.reconstruct_mapping import verify, git


def copy_file(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', required=True, type=Path)
    p.add_argument('--destination', required=True, type=Path)
    a = p.parse_args()
    pin = verify(a.library)
    a.destination.mkdir(parents=True, exist_ok=False)
    for rel in pin['sources']:
        copy_file(a.library / rel, a.destination / 'library' / rel)
    link = git(a.library, 'rev-parse', 'HEAD:3rdparty/fast_float')
    dep = a.library / '3rdparty/fast_float'
    if git(dep, 'rev-parse', 'HEAD') != link or git(dep, 'status', '--porcelain'):
        raise ValueError('pinned public fast_float source missing or dirty')
    raw = subprocess.check_output(['git', '-C', str(dep), 'archive', 'HEAD'])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(a.destination / 'library/3rdparty/fast_float', filter='data')
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
    for rel in paths:
        if not rel:
            continue
        if (rel.startswith('tools/dolby_harness/') and '/analysis/' not in rel or
                rel.startswith('wip/libplacebo-dm/') or rel.startswith('packaging/rog-hdr-dm-experimental/') or
                rel in ('scripts/reconstruct_mapping.py', 'scripts/prepare_mapping_package.py',
                        'scripts/prepare_current_baseline_fixture.py', 'LICENSES.md') or
                rel.startswith('tests/') and Path(rel).name in ('test_absolute_sop.py', 'test_authored_master.py',
                    'test_dolby_harness.py', 'test_dolby_postreshape.py', 'test_mapping_package.py',
                    'test_open_dm.py', 'test_original_targets.py', 'test_public_mapping.py', 'test_sqrtsum.py') or
                rel.startswith('docs/') and Path(rel).name in ('SQRTSUM_PQ_Y_POST.md', 'MAPPING_ABI368_DELIVERY.md')):
            copy_file(ROOT / rel, a.destination / rel)
    shutil.copytree(ROOT / 'packaging/rog-hdr-dm-experimental/debian', a.destination / 'debian')
    (a.destination / 'debian/rules').chmod(0o755)
    manifest = {'schema': 'hdr.abi368.package-source.v1', 'library_identity': pin['identity'],
                'fast_float_gitlink': link, 'repository_head': git(ROOT, 'rev-parse', 'HEAD'),
                'files': {str(path.relative_to(a.destination)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(a.destination.rglob('*')) if path.is_file()}}
    (a.destination / 'PACKAGE-SOURCE.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'source_tree': str(a.destination), 'files': len(manifest['files']),
                      'builds_run': 0, 'units_run': 0}))


if __name__ == '__main__':
    main()
