#!/usr/bin/env python3
"""Compile unchanged consumer with package-relative RUNPATH, never execute it.

A distinct compile schema deliberately cannot pass open_dm_provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', type=Path, default=ROOT / 'library')
    p.add_argument('--build', type=Path, default=ROOT / 'build')
    p.add_argument('--output', type=Path, default=ROOT / 'build/package-consumer')
    a = p.parse_args()
    pin = json.loads((ROOT / 'wip/libplacebo-dm/public-rgb/SOURCE.json').read_text())
    for rel, digest in pin['sources'].items():
        if sha(a.library / rel) != digest:
            raise ValueError('frozen library source differs: ' + rel)
    a.output.mkdir(parents=True, exist_ok=False)
    flags = shlex.split(subprocess.check_output(['dpkg-buildflags', '--get', 'CFLAGS'], text=True))
    links = shlex.split(subprocess.check_output(['dpkg-buildflags', '--get', 'LDFLAGS'], text=True))
    cmd = ['cc', '-std=c11', '-O2', '-g', '-fno-fast-math', '-Wall', '-Wextra', '-Werror',
           *flags, '-ffile-prefix-map=' + str(ROOT) + '=/usr/src/rog-hdr-dm-experimental',
           '-I' + str(a.build / 'src/include'), '-I' + str(a.library / 'src/include'),
           str(ROOT / 'tools/dolby_harness/open_dm_render.c'),
           '-MD', '-MF', str(a.output / 'compile.d'),
           '-L' + str(a.build / 'src'), *links,
           '-Wl,-z,origin', '-Wl,-rpath,$ORIGIN/../../lib/rog-hdr-dm-experimental',
           '-lplacebo', '-lm', '-o', str(a.output / 'open-dm-render')]
    with (a.output / 'compile.stdout').open('xb') as out, (a.output / 'compile.stderr').open('xb') as err:
        subprocess.run(cmd, check=True, stdout=out, stderr=err)
    deps = shlex.split((a.output / 'compile.d').read_text().replace('\\\n', ' ').split(':', 1)[1])
    # Keep exact private compile paths/hashes in task build evidence, not public artifacts.
    actual = {str(Path(name).resolve(strict=True)): sha(name) for name in deps}
    receipt = {'schema': 'hdr.abi368.package-compile.v1', 'status': 'compiled-not-executed',
               'library_identity': pin['identity'], 'library_sources': pin['sources'],
               'consumer_source_sha256': sha(ROOT / 'tools/dolby_harness/open_dm_render.c'),
               'build_recipe_sha256': sha(__file__), 'command': cmd,
               'compiler': subprocess.check_output(['cc', '--version'], text=True),
               'dependencies': actual, 'binary_sha256': sha(a.output / 'open-dm-render'),
               'library_sha256': sha(a.build / 'src/libplacebo.so.368'),
               'units_run': 0, 'renders_run': 0}
    (a.output / 'compile-private.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'schema': receipt['schema'], 'binary_sha256': receipt['binary_sha256'],
                      'units_run': 0, 'renders_run': 0}))


if __name__ == '__main__':
    main()
