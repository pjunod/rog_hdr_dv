#!/usr/bin/env python3
"""Compile/link the pinned consumer in an owned native Linux directory.

No tests, GPU probes, package installation or network access. Inputs must have
been acquired and extracted beforehand. A receipt binds sources, headers, ELF,
compiler command and the inspected loader/CPU ICD closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_elf(path):
    run = subprocess.run(['ldd', str(path)], check=True, capture_output=True, text=True)
    if 'not found' in run.stdout:
        raise ValueError('unresolved runtime dependency')
    paths = set(re.findall(r'(/[^\s()]+)\s+\(', run.stdout))
    return {str(Path(p).resolve()): sha(p) for p in sorted(paths)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix', required=True)
    p.add_argument('--output', required=True, help='new owned build directory')
    args = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('stage1 qualification build requires native x86_64 Linux')
    prefix = Path(args.prefix).resolve(strict=True)
    build = Path(args.output).resolve()
    build.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    consumer = root / 'tools/dolby_harness/headless_render.c'
    library = prefix / 'usr/lib/x86_64-linux-gnu'
    compiler = shutil.which('cc')
    if compiler is None:
        raise ValueError('native C compiler absent')
    cmd = [compiler, '-std=c11', '-O2', '-fno-fast-math', '-Wall', '-Wextra', '-Werror',
           '-I' + str(prefix / 'usr/include'), '-I' + str(prefix / 'include'),
           str(consumer), '-L' + str(library), '-Wl,-rpath,' + str(library),
           '-lplacebo', '-lm', '-o', str(build / 'headless-render')]
    with (build / 'compile.stdout').open('wb') as out, (build / 'compile.stderr').open('wb') as err:
        proc = subprocess.run(cmd, stdout=out, stderr=err, timeout=120)
    if proc.returncode:
        raise ValueError('compiler failed; retained ' + str(build / 'compile.stderr'))
    headers = [*sorted((prefix / 'usr/include/libplacebo').rglob('*.h')),
               *sorted((prefix / 'include').rglob('*.h'))]
    source_paths = [*sorted((root / 'tools/dolby_harness').glob('*.py')),
                    consumer, root / 'tools/dolby_harness/dependencies.json',
                    root / 'tests/test_dolby_harness.py']
    runtime = inspect_elf(build / 'headless-render')
    icd = Path('/usr/share/vulkan/icd.d/lvp_icd.json')
    icd_data = json.loads(icd.read_text())
    if icd_data['ICD']['library_path'] != 'libvulkan_lvp.so':
        raise ValueError('unexpected CPU ICD library path; bind explicitly before build')
    cpu = Path('/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so').resolve(strict=True)
    runtime.update(inspect_elf(cpu))
    runtime[str(cpu)] = sha(cpu)
    runtime[str(icd)] = sha(icd)
    receipt = {'schema': 1, 'status': 'compiled-not-executed',
               'architecture': platform.machine(),
               'sources': {str(p.relative_to(root)): sha(p) for p in source_paths},
               'headers': {str(p.relative_to(prefix)): sha(p) for p in headers},
               'compiler': subprocess.check_output(['cc', '--version'], text=True),
               'compiler_sha256': sha(Path(compiler).resolve()),
               'command': cmd, 'binary_sha256': sha(build / 'headless-render'),
               'runtime': runtime,
               'compile_stdout_sha256': sha(build / 'compile.stdout'),
               'compile_stderr_sha256': sha(build / 'compile.stderr'),
               'units_run': 0, 'render_probes_run': 0}
    (build / 'compile-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'compiled': True, 'binary_sha256': receipt['binary_sha256'],
                      'receipt': str(build / 'compile-receipt.json'), 'units_run': 0}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
