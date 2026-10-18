#!/usr/bin/env python3
"""Compile the separate OPEN consumer against an exact private ABI368 build.

No tests or renders. Source manifest is generated from the committed library by
source export tooling; all actual files are checked before and after compilation.
"""
import argparse
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

from tools.dolby_harness import open_dm_provenance as p
from tools.dolby_harness.contracts import parse_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library-source', 'library-build', 'source-manifest', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('native x86_64 Linux required')
    source = Path(args.library_source).resolve(strict=True)
    build = Path(args.library_build).resolve(strict=True)
    manifest_raw = Path(args.source_manifest).read_bytes()
    manifest = parse_json(manifest_raw)
    def verify():
        for rel, digest in manifest['sources'].items():
            if p.sha(source / rel) != digest:
                raise ValueError('library compile source mismatch: ' + rel)
    verify()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler_path = shutil.which('cc')
    if not compiler_path:
        raise ValueError('native C compiler absent')
    compiler = Path(compiler_path).resolve(strict=True)
    native = output / 'open-dm-render'
    library = (build / 'src/libplacebo.so.368').resolve(strict=True)
    cmd = [str(compiler), '-std=c11', '-O2', '-fno-fast-math', '-Wall', '-Wextra', '-Werror',
           '-MD', '-MF', str(output / 'compile.d'),
           '-I' + str(build / 'src/include'), '-I' + str(source / 'src/include'),
           str(p.ROOT / 'tools/dolby_harness/open_dm_render.c'),
           '-L' + str(build / 'src'), '-Wl,-rpath,' + str(build / 'src'),
           '-lplacebo', '-lm', '-o', str(native)]
    env = p.native_environment(output)
    with (output / 'compile.stdout').open('wb') as out, (output / 'compile.stderr').open('wb') as err:
        proc = subprocess.run(cmd, env=env, stdout=out, stderr=err, timeout=120)
    if proc.returncode:
        raise ValueError('OPEN compiler failed; retained ' + str(output))
    verify()
    dependency_text = (output / 'compile.d').read_text().replace('\\\n', ' ')
    dependencies = shlex.split(dependency_text.split(':', 1)[1])
    actual_dependencies = {str(Path(path).resolve(strict=True)): p.sha(path) for path in dependencies}
    if str((p.ROOT / 'tools/dolby_harness/open_dm_render.c').resolve()) not in actual_dependencies:
        raise ValueError('compiler dependency closure omitted actual consumer source')
    headers = [*sorted((source / 'src/include').rglob('*.h')),
               *sorted((build / 'src/include').rglob('*.h'))]
    # One root retains both generated and source headers without path ambiguity.
    header_root = output / 'headers'
    hashes = {}
    for path in headers:
        group = 'generated' if path.is_relative_to(build) else 'source'
        origin = build / 'src/include' if group == 'generated' else source / 'src/include'
        rel = group + '/' + str(path.relative_to(origin))
        dest = header_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        hashes[rel] = p.sha(dest)
    runtime = p.base.resolved_dependencies(native, env)
    runtime.update(p.base.resolved_dependencies(p.base.CPU, env))
    runtime[str(p.base.CPU.resolve(strict=True))] = p.sha(p.base.CPU)
    runtime[str(p.base.ICD)] = p.sha(p.base.ICD)
    if runtime.get(str(library)) != p.sha(library):
        raise ValueError('actual loader did not select private ABI368 library')
    receipt = {'schema': p.SCHEMA, 'status': 'compiled-not-executed', 'abi': 368,
               'architecture': platform.machine(), 'command': cmd,
               'compiler': subprocess.check_output([str(compiler), '--version'], text=True),
               'compiler_sha256': p.sha(compiler), 'binary_sha256': p.sha(native),
               'library_file': str(library), 'library_sha256': p.sha(library),
               'library_root': str(source), 'library_identity': manifest['identity'],
               'library_sources': manifest['sources'], 'source_manifest_sha256': p.base.sha_bytes(manifest_raw),
               'header_root': str(header_root), 'headers': hashes,
               'actual_headers': {str(path): p.sha(path) for path in headers},
               'compiler_dependencies': actual_dependencies,
               'sources': {rel: p.sha(p.ROOT / rel) for rel in p.COMPILE_INPUTS},
               'runtime': runtime, 'compile_stdout_sha256': p.sha(output / 'compile.stdout'),
               'compile_stderr_sha256': p.sha(output / 'compile.stderr'), 'units_run': 0, 'renders_run': 0}
    p.validate_compile(receipt, live=True)
    (output / 'compile-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'compiled': True, 'abi': 368, 'binary_sha256': receipt['binary_sha256'], 'units_run': 0}))


if __name__ == '__main__':
    main()
