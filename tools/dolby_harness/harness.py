#!/usr/bin/env python3
"""Headless renderer front end and strict private-reference comparison CLI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from tools.dolby_harness.contracts import (ENCODING, alignment, input_manifest,
                                         pixels, result_manifest)
from tools.dolby_harness.metric import compare_pixels
from tools.dolby_harness.provenance import (execution_binding, implementation,
                                           native_environment, sha_bytes)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def control(obj, metadata):
    f, s, t = obj['frame'], obj['source'], obj['target']
    values = ['DVH1', f['width'], f['height'],
              ('rgb', 'bt2020nc', 'dolbyvision').index(s['system']),
              ('full', 'limited').index(s['range']), s['bit_depth']]
    for vol in (s['mastering'], t):
        values += [vol['min_nits'], vol['max_nits'], *vol['primaries']]
    values += [metadata['max_pq_y'] if metadata else 0,
               metadata['avg_pq_y'] if metadata else 0]
    if s['system'] == 'dolbyvision' and metadata:
        values += metadata['nonlinear_offset']
        for matrix in ('nonlinear', 'linear'):
            values += [x for row in metadata[matrix] for x in row]
        for comp in metadata['comp']:
            values += [len(comp['pivots']), *comp['pivots']]
            for seg in comp['segments']:
                if seg['method'] == 'polynomial':
                    values += [0, *seg['coefficients']]
                else:
                    values += [1, seg['order'], seg['constant']]
                    values += [x for row in seg['coefficients'] for x in row]
    return ' '.join(str(x) for x in values) + '\n'


def baseline_semantics(obj, metadata):
    s = obj['source']
    dovi = s['system'] == 'dolbyvision'
    native_l1 = [struct.unpack('<f', struct.pack('<f', metadata[k]))[0]
                 if metadata else 0 for k in ('max_pq_y', 'avg_pq_y')]
    result = {'pq_minima': {
                'requested_source_nits': s['mastering']['min_nits'],
                'requested_target_nits': obj['target']['min_nits'],
                'effective_nominal_source_nits': 1e-6,
                'effective_nominal_target_nits': 1e-6,
                'policy': 'all PQ metadata minima ignored (PL_COLOR_HDR_BLACK)'},
            'range': {'attested_base_layer_range': s['range'],
                      'effective_normalization': 'RPU matrices and offsets; no pre-expansion'
                      if dovi else 'explicit ' + s['range'],
                      'samples': 'original codes divided by 2^bit_depth-1'},
            'cie_y_l1': {'requested_max_pq_y': metadata['max_pq_y'] if metadata else None,
                         'requested_avg_pq_y': metadata['avg_pq_y'] if metadata else None,
                         'native_max_pq_y': native_l1[0],
                         'native_avg_pq_y': native_l1[1],
                         'recognized': bool(native_l1[0] and native_l1[1]),
                         'fallback': 'mastering/color-space baseline when either L1 value is zero'},
            'l1_minimum': 'not implemented', 'trims': 'not implemented'}
    if obj['schema'] == 2:
        result['post_reshape'] = {
            'translation': metadata['translation'], 'raw_l1': metadata['l1'],
            'scope': 'direct normalized Dolby XML L1 translation into upstream slots; not proven photometric CIE-Y or RPU equivalence',
            'unsupported_levels': ['L1 minimum', 'L2', 'L3', 'L8'],
            'l9': 'source declaration verified; no dynamic L9 processing'}
    return result


def render(manifest, native, output, compile_receipt=None):
    manifest_raw = Path(manifest).read_bytes()
    obj, source, metadata = input_manifest(manifest, manifest_raw)
    output = Path(output).resolve()
    native = Path(native).resolve(strict=True)
    if output.exists():
        raise ValueError('output directory already exists; never overwrite a receipt')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.harness-', dir=output.parent))
    try:
        # Snapshot verified inputs, not a second unchecked open by the renderer.
        shutil.copyfile(source, stage / 'source.f32')
        if sha(stage / 'source.f32') != obj['frame']['input']['sha256']:
            raise ValueError('source changed while staging')
        (stage / 'control.txt').write_text(control(obj, metadata))
        (stage / 'input-manifest.json').write_bytes(manifest_raw)
        receipt_path = Path(compile_receipt) if compile_receipt else native.parent / 'compile-receipt.json'
        (stage / 'compile-receipt.json').write_bytes(receipt_path.read_bytes())
        env = native_environment(stage)
        binding = execution_binding(native, stage / 'compile-receipt.json', env)
        with (stage / 'native.stdout').open('wb') as out, (stage / 'native.stderr').open('wb') as err:
            proc = subprocess.run([str(native), str(stage / 'control.txt'),
                                   str(stage / 'source.f32'), str(stage / 'output.f32')],
                                  env=env, stdout=out, stderr=err, timeout=180)
        if proc.returncode:
            raise ValueError('native renderer failed (exit ' + str(proc.returncode) + ')')
        if execution_binding(native, stage / 'compile-receipt.json', env) != binding:
            raise ValueError('execution inputs changed during render')
        pixels(stage / 'output.f32', obj['frame']['width'], obj['frame']['height'])
        receipt = {'schema': obj['schema'], 'role': 'candidate', 'alignment': alignment(obj, metadata),
                   'encoding': ENCODING,
                   'output': {'file': 'output.f32', 'sha256': sha(stage / 'output.f32')},
                   'provenance': {'implementation': 'source-bound libplacebo baseline',
                                  'execution': binding,
                                  'input_manifest_sha256': sha_bytes(manifest_raw),
                                  'baseline_semantics': baseline_semantics(obj, metadata),
                                  'control_sha256': sha(stage / 'control.txt'),
                                  'stdout_sha256': sha(stage / 'native.stdout'),
                                  'stderr_sha256': sha(stage / 'native.stderr'),
                                  'device': (stage / 'native.stdout').read_text().strip(),
                                  'peak_detection': False, 'dithering': False,
                                  'scaling': False, 'trims': 'not implemented'}}
        (stage / 'candidate.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
        (stage / 'source.f32').unlink()
        os.rename(stage, output)
        return output / 'candidate.json'
    except Exception as exc:
        # Retain actual failed compiler/runtime diagnostics privately, no fake output.
        raise ValueError(str(exc) + '; retained diagnostics: ' + str(stage)) from exc


def compare(candidate, reference):
    frontend = implementation()
    candidate_raw = Path(candidate).read_bytes()
    reference_raw = Path(reference).read_bytes()
    a, pa = result_manifest(candidate, candidate_raw)
    b, pb = result_manifest(reference, reference_raw)
    if a['role'] != 'candidate' or b['role'] != 'reference':
        raise ValueError('candidate and reference roles required')
    if a['schema'] != b['schema'] or a['alignment'] != b['alignment']:
        raise ValueError('source/metadata/target/frame alignment mismatch')
    return {'schema': a['schema'], 'metric': 'ITU-R BT.2124-0 Annex 1 deltaE_ITP',
            'alignment': a['alignment'], 'encoding': ENCODING,
            'candidate_sha256': a['output']['sha256'],
            'reference_sha256': b['output']['sha256'],
            'provenance': {'candidate_manifest_sha256': sha_bytes(candidate_raw),
                           'reference_manifest_sha256': sha_bytes(reference_raw),
                           'candidate_renderer': a['provenance'],
                           'reference_renderer': b['provenance'],
                           'comparator': frontend},
            'statistics': compare_pixels(pa, pb),
            'scope': 'software pixels only; no certification or optical acceptance'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('render')
    r.add_argument('manifest')
    r.add_argument('--native', required=True)
    r.add_argument('--compile-receipt', help='defaults to compile-receipt.json beside native ELF')
    r.add_argument('--output', required=True)
    c = sub.add_parser('compare')
    c.add_argument('candidate')
    c.add_argument('reference')
    c.add_argument('--report', required=True, help='private report path; numerical comparisons never print')
    args = p.parse_args()
    try:
        if args.command == 'render':
            print(render(args.manifest, args.native, args.output, args.compile_receipt))
        else:
            report = compare(args.candidate, args.reference)
            # Exclusive create; preserve every existing private comparison.
            with Path(args.report).open('x') as out:
                out.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
            print('Comparison saved privately to requested report path')
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print('Harness error: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
