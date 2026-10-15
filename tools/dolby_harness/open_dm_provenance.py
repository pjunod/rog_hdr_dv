"""Source-bound OPEN ABI364 compiler/execution closure, separate from baseline."""
from pathlib import Path
import platform
import sys

from tools.dolby_harness import authored_master as am
from tools.dolby_harness import provenance as base
from tools.dolby_harness.contracts import parse_json
from tools.dolby_harness.master_pixels import read_bounded

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'hdr.open-dm-compile.v1'
COMPILE_INPUTS = ('tools/dolby_harness/open_dm_render.c',
                  'tools/dolby_harness/open_dm_build.py',
                  'tools/dolby_harness/open_dm_provenance.py',
                  'wip/libplacebo-dm/absolute-pq/SOURCE.json')
FRONTEND_INPUTS = (*base.FRONTEND_INPUTS, 'tools/dolby_harness/open_dm.py',
                   'tools/dolby_harness/open_dm_provenance.py')
sha = base.sha
native_environment = base.native_environment
LOADED = {p: sha(ROOT / p) for p in FRONTEND_INPUTS}


def implementation():
    current = {p: sha(ROOT / p) for p in FRONTEND_INPUTS}
    if current != LOADED:
        raise ValueError('OPEN frontend changed since import')
    return {'sources': current, 'python_version': sys.version,
            'python_sha256': sha(Path(sys.executable).resolve(strict=True))}


def validate_compile(receipt, live=False):
    if (receipt.get('schema') != SCHEMA or receipt.get('abi') != 364 or
            receipt.get('architecture') != 'x86_64' or
            receipt.get('status') != 'compiled-not-executed'):
        raise ValueError('OPEN ABI364 compile receipt required')
    for p in COMPILE_INPUTS:
        if receipt['sources'][p] != sha(ROOT / p):
            raise ValueError('OPEN compile input changed: ' + p)
    for key in ('headers', 'actual_headers', 'compiler_dependencies', 'library_sources', 'runtime'):
        if not receipt[key]:
            raise ValueError('OPEN compile closure missing: ' + key)
    identity = receipt['library_identity']
    pinned = parse_json(read_bounded(ROOT / 'wip/libplacebo-dm/absolute-pq/SOURCE.json', 4 * 1024 * 1024))
    if not am.strict_equal(identity, pinned['identity']) or not am.strict_equal(receipt['library_sources'], pinned['sources']):
        raise ValueError('OPEN library differs from committed candidate source pin')
    for key in ('head', 'tree'):
        if not isinstance(identity[key], str) or len(identity[key]) != 40 or any(c not in '0123456789abcdef' for c in identity[key]):
            raise ValueError('OPEN library Git identity malformed')
    # Full tracked source set, not a hardcoded baseline-input bypass. The build
    # supplied Git manifest is retained in the receipt and rehashed on execution.
    required = ('src/dovi_dm.c', 'src/include/libplacebo/dovi_dm.h',
                'src/shaders/colorspace.c', 'src/renderer.c', 'meson.build')
    if any(k not in receipt['library_sources'] for k in required):
        raise ValueError('OPEN library source set incomplete')
    if live:
        for path, digest in receipt['compiler_dependencies'].items():
            if sha(path) != digest:
                raise ValueError('OPEN actual compiler dependency changed: ' + path)
        for path, digest in receipt['actual_headers'].items():
            if sha(path) != digest:
                raise ValueError('OPEN actual compile header changed: ' + path)
        for root, hashes in ((receipt['library_root'], receipt['library_sources']),
                             (receipt['header_root'], receipt['headers'])):
            for rel, digest in hashes.items():
                if sha(Path(root) / rel) != digest:
                    raise ValueError('OPEN source/header changed: ' + rel)
        if sha(receipt['library_file']) != receipt['library_sha256']:
            raise ValueError('OPEN library changed')


def execution_binding(native, receipt_path, env):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('OPEN requires native x86_64 Linux')
    preload = Path('/etc/ld.so.preload')
    if preload.exists() and preload.read_text().strip():
        raise ValueError('system loader preloads forbidden')
    raw = read_bounded(receipt_path, 4 * 1024 * 1024)
    r = parse_json(raw)
    validate_compile(r, live=True)
    if sha(native) != r['binary_sha256']:
        raise ValueError('OPEN native ELF mismatch')
    if parse_json(base.ICD.read_bytes())['ICD']['library_path'] != base.CPU.name:
        raise ValueError('unexpected CPU ICD')
    runtime = base.resolved_dependencies(native, env)
    runtime.update(base.resolved_dependencies(base.CPU, env))
    runtime[str(base.CPU.resolve(strict=True))] = sha(base.CPU)
    runtime[str(base.ICD)] = sha(base.ICD)
    if runtime != r['runtime'] or runtime.get(str(Path(r['library_file']).resolve())) != r['library_sha256']:
        raise ValueError('OPEN loader/runtime mismatch')
    return {'compile_receipt_sha256': base.sha_bytes(raw), 'compile_receipt': r,
            'native_sha256': sha(native), 'runtime': runtime,
            'environment': env, 'frontend': implementation()}


def validate_record(execution, compiled):
    validate_compile(compiled)
    if (not am.strict_equal(execution['compile_receipt'], compiled) or
            execution['native_sha256'] != compiled['binary_sha256'] or
            not am.strict_equal(execution['runtime'], compiled['runtime']) or
            not am.strict_equal(execution['frontend']['sources'], implementation()['sources'])):
        raise ValueError('OPEN result compile/frontend/runtime mismatch')
    # Historical output verification does not pretend to resolve a remote loader
    # anew, but validates the explicit clean execution environment and all hashes.
    env = execution['environment']
    if not am.strict_equal(env, native_environment(Path(env['HOME']))):
        raise ValueError('OPEN execution environment mismatch')
