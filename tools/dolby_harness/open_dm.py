"""Explicit OPEN XML205 PQ-Hermite/SOP diagnostic, never a consumer CM claim.

Only schema3's unchanged original-source verifier supplies metadata. No vendor
invocation, fitting, raw-code quantization or second image tone mapper occurs.
"""
import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from tools.dolby_harness import authored_master as am
from tools.dolby_harness.contracts import (ENCODING, alignment, input_manifest,
                                         parse_json, result_manifest)
from tools.dolby_harness.master_pixels import read_bounded, sha
from tools.dolby_harness.metric import compare_pixels

SCHEMA = 'hdr.open-dm-result.v1'
ALGORITHM = 'open-xml205-hermite-pq-sop-v1'
VARIANTS = ('l1-rational', 'l1-hermite', 'l1-hermite-sop')
HYPOTHESES = [
    'Public US10600166B2 Table1/Eq7 with improved0080-0082, not identified consumer CM',
    'XML Lift/Gain/Gamma serializer algebra and Eq1 delta-to-factor are OPEN applicability hypotheses',
    'Normalized PQ intensity placed at existing HPE-LMS/PQ/IPT I, not proven consumer intensity',
    'Final physical clamp and collapsed-anchor handling are engineering policies, not patent rules',
    'Existing L1 chroma compensation retained once before SOP; consumer equivalence unproven',
]


def factors(trim):
    """Exact original decimals -> frozen public/algebraic OPEN actual factors."""
    tokens = trim.split(',')
    am.decimals(trim, 9, -1e6, 1e6)
    lift, gain, gamma = [Fraction(x) for x in tokens[3:6]]
    if not -1 <= lift <= 1 or not -1 <= gain <= 1:
        raise ValueError('OPEN Lift/Gain supported range is [-1,1]')
    clipped = min(Fraction(1), max(Fraction(-1), gamma))
    physical_gain, physical_lift = 1 + gain / 2, lift / 2
    physical_gamma = 1 + clipped / 2
    clip = lambda x: min(Fraction(1, 2), max(Fraction(-1, 2), x))
    exact = {'S': 1 + clip(physical_gain * (1 - physical_lift) - 1),
             'O': clip(physical_gain * physical_lift),
             'P': 1 + clip(1 / physical_gamma - 1)}
    return {'exact': {k: str(v) for k, v in exact.items()},
            'float': {k: float(v) for k, v in exact.items()},
            'gamma_original': tokens[5], 'gamma_clamped': str(clipped)}


def algorithm(obj, meta, variant):
    if variant not in VARIANTS or type(obj['schema']) is not int or obj['schema'] != 3:
        raise ValueError('OPEN candidate requires schema3 and a fixed variant')
    if not am.strict_equal(obj['target'], {'id': '27', 'min_nits': 0, 'max_nits': 600, 'primaries': am.P3}):
        raise ValueError('only exact original target27/600nit/0black/P3D65 is selected')
    selected = [r for r in meta['records'] if r['level'] == 2 and r['target_id'] == 27]
    if not selected:
        raise ValueError('original target27 Trim required')
    trims = [next(f['text'] for f in r['fields'] if f['name'] == 'Trim') for r in selected]
    if len(set(trims)) != 1:
        raise ValueError('conflicting frame/shot Trim')
    derived = factors(trims[0])
    applied = derived['float'] if variant == 'l1-hermite-sop' else {'S': 1.0, 'O': 0.0, 'P': 1.0}
    l1 = meta['l1']
    branch = ('flat-source' if l1['min_pq'] == l1['max_pq'] else
              'collapsed-tail' if l1['min_pq'] == l1['avg_pq'] else
              'collapsed-head' if l1['avg_pq'] == l1['max_pq'] else 'regular')
    return {'id': ALGORITHM, 'variant': variant,
            'domain': 'normalized-PQ; existing HPE-LMS/PQ/IPT I placement',
            'l1_curve_domain': 'nits rational' if variant == 'l1-rational' else 'normalized-PQ analytic Hermite',
            'l1': l1, 'l1_presence': True, 'degenerate_branch': branch,
            'target': obj['target'], 'target_generation': 1, 'target_description_id': 27,
            'source_records': meta['records'], 'selected_records': selected,
            'original_trim': trims[0], 'derived_factors': derived, 'applied_factors': applied,
            'selected_cm_name': None, 'algorithm_versions': meta['algorithm_versions'],
            'curve_defaults': {'preservation_tail': 0.5, 'preservation_head': 0.5,
                               'cutoff': 0.5, 'contrast': 1, 'tail_power': 2, 'head_power': 4},
            'applied_stages': ['explicit presence-aware L1', 'existing L1 chroma compensation once'] +
                              (['OPEN target-normalized PQ SOP'] if variant == 'l1-hermite-sop' else []) +
                              ['existing final physical gamut mapping once'],
            'unapplied_trim_indexes': [0, 1, 2, 6, 7, 8],
            'unapplied_trim_values': {str(i): trims[0].split(',')[i] for i in (0, 1, 2, 6, 7, 8)},
            'unapplied_stages': ['chroma', 'saturation', 'detail', 'L3', 'L8', 'midcontrast',
                                 'CM selection', 'temporal rules', 'target interpolation', 'raw-RPU SOP'],
            'hypotheses': HYPOTHESES, 'full_mapping_complete': False}


def control(obj, meta, variant):
    a = algorithm(obj, meta, variant)
    values = ['DVH3', obj['frame']['width'], obj['frame']['height'], 1]
    for v in (obj['source']['mastering'], obj['target']):
        values += [v['min_nits'], v['max_nits'], *v['primaries']]
    values += [meta['l1'][k] for k in ('min_pq', 'avg_pq', 'max_pq')]
    values += [VARIANTS.index(variant)] + [a['applied_factors'][k] for k in ('S', 'O', 'P')]
    return ' '.join(str(x) for x in values) + '\n'


def render(manifest, variant, native, compile_receipt, output):
    from tools.dolby_harness import open_dm_provenance as prov
    raw = read_bounded(manifest, 4 * 1024 * 1024)
    obj, source, meta = input_manifest(manifest, raw)
    algo = algorithm(obj, meta, variant)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('never overwrite an existing candidate')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.open-dm-', dir=output.parent))
    try:
        shutil.copyfile(source, stage / 'source.f32')
        if prov.sha(stage / 'source.f32') != obj['frame']['input']['sha256']:
            raise ValueError('source changed while staging')
        (stage / 'control.txt').write_text(control(obj, meta, variant))
        (stage / 'compile-receipt.json').write_bytes(read_bounded(compile_receipt, 4 * 1024 * 1024))
        env = prov.native_environment(stage)
        native = Path(native).resolve(strict=True)
        binding = prov.execution_binding(native, stage / 'compile-receipt.json', env)
        with (stage / 'native.stdout').open('wb') as out, (stage / 'native.stderr').open('wb') as err:
            proc = subprocess.run([str(native), str(stage / 'control.txt'), str(stage / 'source.f32'),
                                   str(stage / 'output.f32')], env=env, stdout=out, stderr=err, timeout=180)
        if proc.returncode:
            raise ValueError('OPEN native render failed: ' + str(proc.returncode))
        if prov.execution_binding(native, stage / 'compile-receipt.json', env) != binding:
            raise ValueError('OPEN execution inputs changed during rendering')
        f = obj['frame']
        pixels = read_bounded(stage / 'output.f32', f['width'] * f['height'] * 12)
        if len(pixels) != f['width'] * f['height'] * 12:
            raise ValueError('OPEN output geometry mismatch')
        am.pixel_samples(pixels)
        result = {'schema': SCHEMA, 'role': 'candidate', 'source_alignment': alignment(obj, meta),
                  'encoding': ENCODING, 'algorithm': algo,
                  'output': {'file': 'output.f32', 'sha256': sha(pixels)},
                  'provenance': {'input_manifest': {'file': str(Path(manifest).resolve()), 'sha256': sha(raw)},
                                 'execution': binding, 'protocol': 'DVH3',
                                 'control_sha256': prov.sha(stage / 'control.txt'),
                                 'stdout_sha256': prov.sha(stage / 'native.stdout'),
                                 'stderr_sha256': prov.sha(stage / 'native.stderr'),
                                 'target': obj['target'], 'target_generation': 1, 'target_description_id': 27}}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        (stage / 'source.f32').unlink()
        os.rename(stage, output)
        return output / 'candidate.json'
    except Exception as exc:
        raise ValueError(str(exc) + '; retained diagnostics: ' + str(stage)) from exc


@am.validation
def validate_result(path, raw=None):
    from tools.dolby_harness import open_dm_provenance as prov
    path = Path(path)
    r = parse_json(raw if raw is not None else read_bounded(path, 4 * 1024 * 1024))
    am.keys(r, 'schema role source_alignment encoding output algorithm provenance')
    if r['schema'] != SCHEMA or r['role'] != 'candidate' or not am.strict_equal(r['encoding'], ENCODING):
        raise ValueError('OPEN result schema/role/encoding mismatch')
    p = r['provenance']
    manifest, input_raw = am.snapshot(path.parent, p['input_manifest'])
    obj, _, meta = input_manifest(manifest, input_raw)
    if not am.strict_equal(r['source_alignment'], alignment(obj, meta)):
        raise ValueError('OPEN source alignment mismatch')
    variant = r['algorithm']['variant']
    if not am.strict_equal(r['algorithm'], algorithm(obj, meta, variant)):
        raise ValueError('OPEN algorithm metadata/factors mismatch')
    if (not am.strict_equal(p['target'], obj['target']) or
            not am.strict_equal([p['target_generation'], p['target_description_id']], [1, 27])):
        raise ValueError('OPEN immutable target mismatch')
    _, compiled_raw = am.snapshot(path.parent, {'file': 'compile-receipt.json',
                                              'sha256': p['execution']['compile_receipt_sha256']})
    prov.validate_record(p['execution'], parse_json(compiled_raw))
    _, native_control = am.snapshot(path.parent, {'file': 'control.txt', 'sha256': p['control_sha256']})
    if p['protocol'] != 'DVH3' or native_control != control(obj, meta, variant).encode():
        raise ValueError('OPEN native protocol mismatch')
    for name in ('stdout', 'stderr'):
        am.snapshot(path.parent, {'file': 'native.' + name, 'sha256': p[name + '_sha256']})
    normalized = am.output_snapshot(path.parent, r['output'], obj['frame']['width'], obj['frame']['height'])
    return r, am.pixel_samples(normalized)


def compare(candidate, reference):
    from tools.dolby_harness.open_dm_provenance import implementation
    a, pa = validate_result(candidate)
    reference_raw = read_bounded(reference, 4 * 1024 * 1024)
    b, pb = result_manifest(reference, reference_raw)
    if b['schema'] != 3 or b['role'] != 'reference' or not am.strict_equal(a['source_alignment'], b['alignment']):
        raise ValueError('strict same-source retained reference required')
    # Independently validated reference input as well as alignment, never copied.
    if a['provenance']['input_manifest']['sha256'] != b['provenance']['input_manifest']['sha256']:
        raise ValueError('candidate/reference input manifest mismatch')
    return {'schema': 'hdr.open-dm-comparison.v1', 'algorithm': a['algorithm'],
            'source_alignment': a['source_alignment'], 'encoding': ENCODING,
            'candidate_sha256': a['output']['sha256'], 'reference_sha256': b['output']['sha256'],
            'candidate_manifest_sha256': sha(read_bounded(candidate, 4 * 1024 * 1024)),
            'reference_manifest_sha256': sha(reference_raw), 'comparator': implementation(),
            'metric': 'ITU-R BT.2124-0 Annex 1 deltaE_ITP', 'statistics': compare_pixels(pa, pb),
            'scope': 'OPEN fixed diagnostic; not full Dolby/OEM/optical acceptance'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('render')
    r.add_argument('input')
    r.add_argument('--variant', choices=VARIANTS, required=True)
    for name in ('native', 'compile-receipt', 'output'):
        r.add_argument('--' + name, required=True)
    c = sub.add_parser('compare')
    c.add_argument('candidate')
    c.add_argument('reference')
    c.add_argument('--report', required=True)
    args = p.parse_args()
    try:
        if args.command == 'render':
            print(render(args.input, args.variant, args.native, args.compile_receipt, args.output))
        else:
            report = compare(args.candidate, args.reference)
            with Path(args.report).open('x') as out:
                out.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
            print('OPEN comparison saved privately')
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('OPEN diagnostic error: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
