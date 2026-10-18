#!/usr/bin/env python3
"""Private ABI368 CPU-only native file consumer with distinct package receipts.

This is NOT open_dm.render, an official reference, a player or raw-RPU parser.
No historical compiler/frontend provenance checks are relaxed or repointed.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

P = 'rog-hdr-dm-experimental'
ICD = Path('/usr/share/vulkan/icd.d/lvp_icd.json')
CPU = Path('/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON field')
        result[k] = v
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique)


def environment(stage):
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
            'HOME': str(stage), 'TMPDIR': str(stage),
            'XDG_CONFIG_HOME': str(stage), 'XDG_DATA_HOME': str(stage),
            'XDG_CACHE_HOME': str(stage), 'VK_DRIVER_FILES': str(ICD),
            'VK_ICD_FILENAMES': str(ICD), 'VK_LOADER_LAYERS_DISABLE': '~all~',
            'LP_NUM_THREADS': '2'}


def dependencies(path, env):
    r = subprocess.run(['/usr/bin/ldd', str(path)], env=env, check=True,
                       capture_output=True, text=True, timeout=30)
    if 'not found' in r.stdout:
        raise ValueError('unresolved runtime dependency')
    paths = set(re.findall(r'(/[^\s()]+)\s+\(', r.stdout))
    if not paths:
        raise ValueError('empty dynamic closure')
    return {str(Path(p).resolve(strict=True)): sha(p) for p in sorted(paths)}


def installed(prefix, env):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('native x86_64 Linux required')
    preload = Path('/etc/ld.so.preload')
    if preload.exists() and preload.read_text().strip():
        raise ValueError('system loader preloads forbidden')
    manifest_path = prefix / 'usr/share' / P / 'PACKAGE-INSTALLED.json'
    m = read_json(manifest_path)
    if (m.get('schema') != 'hdr.abi368.package-installed.v1' or m.get('package') != P or
            type(m.get('abi')) is not int or m['abi'] != 368 or
            m.get('version') != '0.1.0~abi368.1-0ubuntu26.10.1'):
        raise ValueError('wrong package identity/schema')
    required = {'usr/lib/' + P + '/libplacebo.so.368',
                'usr/libexec/' + P + '/open-dm-render', 'usr/libexec/' + P + '/run.py',
                'usr/share/' + P + '/PACKAGE-COMPILE.json',
                'usr/share/' + P + '/wip/libplacebo-dm/public-rgb/SOURCE.json',
                'usr/share/' + P + '/tools/dolby_harness/open_dm_render.c'}
    if not isinstance(m.get('files'), dict) or not required <= m['files'].keys():
        raise ValueError('incomplete package payload closure')
    for rel, digest in m['files'].items():
        part = PurePosixPath(rel)
        if (part.is_absolute() or '..' in part.parts or str(part) != rel or
                not rel.startswith(('usr/lib/' + P + '/', 'usr/libexec/' + P + '/', 'usr/share/' + P + '/'))):
            raise ValueError('unsafe package manifest path')
        path = prefix / rel
        if path.resolve(strict=True) != path or sha(path) != digest:
            raise ValueError('package payload mismatch: ' + rel)
    share = prefix / 'usr/share' / P
    compile_record = read_json(share / 'PACKAGE-COMPILE.json')
    source_pin = read_json(share / 'wip/libplacebo-dm/public-rgb/SOURCE.json')
    if (compile_record.get('schema') != 'hdr.abi368.package-compile.v1' or
            compile_record.get('library_identity') != source_pin['identity'] or
            compile_record.get('library_sources') != source_pin['sources'] or
            compile_record.get('consumer_source_sha256') != sha(share / 'tools/dolby_harness/open_dm_render.c')):
        raise ValueError('package compile/source identity mismatch')
    if read_json(ICD)['ICD']['library_path'] != CPU.name:
        raise ValueError('unexpected CPU Vulkan ICD')
    native = prefix / 'usr/libexec' / P / 'open-dm-render'
    library = prefix / 'usr/lib' / P / 'libplacebo.so.368'
    runtime = dependencies(native, env)
    if runtime.get(str(library)) != sha(library):
        raise ValueError('loader did not resolve exact installed private ABI368')
    runtime.update(dependencies(CPU, env))
    runtime[str(CPU.resolve(strict=True))] = sha(CPU)
    runtime[str(ICD)] = sha(ICD)
    return {'schema': 'hdr.abi368.package-runtime.v1', 'package': P, 'version': m['version'],
            'installed_manifest_sha256': sha(manifest_path), 'files': m['files'],
            'runtime': runtime, 'environment': env,
            'scope': 'package/native integrity only; NOT historical harness or vendor provenance'}


def durable_stage(path):
    stage = path.expanduser().resolve()
    if any(stage == p or stage.is_relative_to(p) for p in
           (Path('/tmp'), Path('/private/tmp'), Path('/var/tmp'), Path('/private/var/tmp'))):
        raise ValueError('durable task-owned stage required, not system temporary storage')
    stage.mkdir(parents=True, exist_ok=False)
    return stage


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspect', action='store_true', help='record loader closure only; do not execute consumer')
    p.add_argument('--stage', required=True, type=Path, help='new durable writable output directory')
    p.add_argument('control', nargs='?', type=Path)
    p.add_argument('input', nargs='?', type=Path)
    a = p.parse_args()
    if (a.inspect and (a.control or a.input)) or (not a.inspect and (not a.control or not a.input)):
        p.error('provide CONTROL INPUT for native render, or --inspect alone')
    prefix = Path(__file__).resolve(strict=True).parents[3]
    stage = durable_stage(a.stage)
    env = environment(stage)
    before = installed(prefix, env)
    (stage / 'runtime-before.json').write_text(json.dumps(before, indent=2) + '\n')
    if a.inspect:
        print('Package loader inspection recorded; no consumer/render executed: ' + str(stage))
        return 0
    raw = a.control.read_bytes()
    if len(raw) > 65536:
        raise ValueError('control exceeds resource bound')
    tokens = raw.decode('ascii').split()
    if len(tokens) != 34 or tokens[0] != 'DVH4' or tokens[28] != '7':
        raise ValueError('packaged interface requires explicit DVH4 SQRTSUM variant7')
    width, height, target = map(int, (tokens[1], tokens[2], tokens[4]))
    if not (1 <= width <= 4096 and 1 <= height <= 2160 and 1 <= target <= 65535):
        raise ValueError('bounded geometry/original target required')
    with a.input.open('rb') as stream:
        pixels = stream.read(width * height * 12 + 1)
    if len(pixels) != width * height * 12:
        raise ValueError('exact tightly packed RGB-f32le geometry required')
    (stage / 'control.txt').write_bytes(raw)
    (stage / 'input.f32').write_bytes(pixels)
    native = prefix / 'usr/libexec' / P / 'open-dm-render'
    with (stage / 'native.stdout').open('xb') as out, (stage / 'native.stderr').open('xb') as err:
        r = subprocess.run([str(native), str(stage / 'control.txt'), str(stage / 'input.f32'),
                            str(stage / 'output.f32')], env=env, stdout=out, stderr=err, timeout=180)
    after = installed(prefix, env)
    if before != after:
        raise ValueError('package/runtime changed during execution')
    if r.returncode:
        raise ValueError('native consumer failed; diagnostics retained: ' + str(stage))
    records = [json.loads(line, object_pairs_hook=unique) for line in (stage / 'native.stdout').read_text().splitlines() if line.startswith('{')]
    config = {'protocol': 'DVH4', 'target_description_id': target, 'RGBA_components': 4,
              'independent_alpha': True, 'background': 'skip', 'background_transparency': 1,
              'blend': False, 'tiles': False, 'hooks': 0, 'lut': False, 'distortion': False}
    domain = {'schema': 'hdr.sqrtsum.gpu-domain.v1', 'population': width * height,
              'valid': width * height, 'invalid': 0, 'channel': 'downloaded-RGBA-alpha-exact1'}
    # JSON textual canonical comparison preserves bool/int distinction.
    if json.dumps(records, sort_keys=True) != json.dumps([config, domain], sort_keys=True):
        raise ValueError('actual native config/whole-download alpha validity mismatch')
    if (stage / 'output.f32').stat().st_size != width * height * 12:
        raise ValueError('native output geometry mismatch')
    receipt = {'schema': 'hdr.abi368.package-native-result.v1', 'runtime': before,
               'input_sha256': sha(stage / 'input.f32'), 'control_sha256': sha(stage / 'control.txt'),
               'output_sha256': sha(stage / 'output.f32'), 'stdout_sha256': sha(stage / 'native.stdout'),
               'stderr_sha256': sha(stage / 'native.stderr'), 'gpu_domain': domain,
               'scope': 'raw native DVH4 caller inputs; no authored/vendor/reference association claimed'}
    (stage / 'PACKAGE-RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(stage / 'PACKAGE-RESULT.json')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('ABI368 package consumer error: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
