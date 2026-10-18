"""Verify retained compiler identity and a controlled native execution closure.

No compile or renderer execution here. Compiler Python/test source hashes are
historical; the front end is separately bound to its current implementation.
"""
import hashlib
from pathlib import Path
import platform
import re
import subprocess
import sys

from tools.dolby_harness.contracts import parse_json

ROOT = Path(__file__).resolve().parents[2]
ICD = Path('/usr/share/vulkan/icd.d/lvp_icd.json')
CPU = Path('/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so')
COMPILE_INPUTS = ('tools/dolby_harness/headless_render.c',
                  'tools/dolby_harness/build.py',
                  'tools/dolby_harness/dependencies.json')
FRONTEND_INPUTS = ('tools/dolby_harness/harness.py',
                   'tools/dolby_harness/contracts.py',
                   'tools/dolby_harness/metric.py',
                   'tools/dolby_harness/provenance.py',
                   'tools/dolby_harness/postreshape.py',
                   'tools/dolby_harness/authored_master.py',
                   'tools/dolby_harness/master_pixels.py')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


# Bind the source snapshot at import, then refuse a changed implementation.
# Qualification starts a fresh interpreter on the exported candidate.
LOADED_SOURCES = {p: sha(ROOT / p) for p in FRONTEND_INPUTS}


def implementation():
    current = {p: sha(ROOT / p) for p in FRONTEND_INPUTS}
    if current != LOADED_SOURCES:
        raise ValueError('front-end source changed since import; start a fresh interpreter')
    return {'sources': current, 'python_version': sys.version,
            'python_sha256': sha(Path(sys.executable).resolve(strict=True))}


def native_environment(stage):
    # Do not inherit LD_*, VK_*, MESA_*, XDG_*, HOME, PATH or layer settings.
    # No display server is reachable from this headless child environment.
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
            'HOME': str(stage), 'XDG_CONFIG_HOME': str(stage),
            'XDG_DATA_HOME': str(stage), 'XDG_CACHE_HOME': str(stage),
            'VK_DRIVER_FILES': str(ICD), 'VK_ICD_FILENAMES': str(ICD),
            'VK_LOADER_LAYERS_DISABLE': '~all~', 'LP_NUM_THREADS': '2'}


def resolved_dependencies(path, env):
    run = subprocess.run(['/usr/bin/ldd', str(path)], env=env, check=True,
                         capture_output=True, text=True, timeout=30)
    if 'not found' in run.stdout:
        raise ValueError('unresolved native runtime dependency')
    paths = set(re.findall(r'(/[^\s()]+)\s+\(', run.stdout))
    if not paths:
        raise ValueError('native dynamic dependency closure absent')
    return {str(Path(p).resolve(strict=True)): sha(p) for p in sorted(paths)}


def execution_binding(native, receipt_path, env):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('render requires native x86_64 Linux')
    preload = Path('/etc/ld.so.preload')
    if preload.exists() and preload.read_text().strip():
        raise ValueError('system loader preloads are not part of the pinned runtime')
    raw = Path(receipt_path).read_bytes()
    receipt = parse_json(raw)
    if (receipt.get('schema') != 1 or receipt.get('architecture') != 'x86_64'
            or receipt.get('status') != 'compiled-not-executed'):
        raise ValueError('source-bound compile receipt required')
    if sha(native) != receipt['binary_sha256']:
        raise ValueError('native ELF/compile receipt mismatch')
    for p in COMPILE_INPUTS:
        if sha(ROOT / p) != receipt['sources'][p]:
            raise ValueError('native compile input changed: ' + p)
    if not receipt.get('headers'):
        raise ValueError('compile receipt header bindings absent')
    # Verify actual loader resolution, not merely the files named by a receipt.
    # Both inspections and rendering use the SAME clean environment.
    icd_raw = ICD.read_bytes()
    if parse_json(icd_raw)['ICD']['library_path'] != CPU.name:
        raise ValueError('unexpected CPU ICD binding')
    runtime = resolved_dependencies(native, env)
    runtime.update(resolved_dependencies(CPU, env))
    runtime[str(CPU.resolve(strict=True))] = sha(CPU)
    runtime[str(ICD)] = sha_bytes(icd_raw)
    if runtime != receipt['runtime']:
        raise ValueError('resolved native runtime/compile receipt mismatch')
    return {'compile_receipt_sha256': sha_bytes(raw),
            'compile_receipt': receipt, 'native_sha256': sha(native),
            'runtime': runtime, 'environment': env,
            'frontend': implementation()}
