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
ABSOLUTE_VARIANT = 'l1-hermite-sop-absolute-pq'
ABSOLUTE_ALGORITHM = 'open-xml205-hermite-absolute-pq-sop-v1'
VARIANTS = ('l1-rational', 'l1-hermite', 'l1-hermite-sop', ABSOLUTE_VARIANT)
RGB_VARIANT = 'rgb-pq-pre-rational'
Y_VARIANT = 'y-pq-pre-rational'
MB_VARIANT = 'y-pq-pre-mastblack'
SQRTSUM_VARIANT = 'y-pq-post-sqrtsum'
VARIANTS += (RGB_VARIANT, Y_VARIANT, MB_VARIANT, SQRTSUM_VARIANT)
SOP_VARIANTS = ('l1-hermite-sop', ABSOLUTE_VARIANT, RGB_VARIANT, Y_VARIANT, MB_VARIANT, SQRTSUM_VARIANT)
FROZEN_DECISIONS = {
    'spec_sha256': '3179434d7e0a88dfd50ec61f7df2a7db9b7fac04e062d2c2ad49a05160046183',
    'parameter_decision_sha256': '0d418f1915ba26faf713ce6eae23e16aa67eacd025ba5cc5122729700c6d99e1',
    'historical_decision_export_sha256': 'e3fa8aaa9d69eae6b483eb0b53a3ec9df4500f2fd4739441b5bcdd8649d4c6fc',
    'public_curve_contract_sha256': 'b4874602eb675d0f9be379c23ea7cd41c2c2aee8544c90eeea45be9c27ffce4c',
    'limit': 'Precomparison policy/derivation identities, not the current relocated export or a reference observation',
}
ABSOLUTE_DECISIONS = {
    **FROZEN_DECISIONS,
    'absolute_domain_spec_sha256': '41fa7c8d6c5ea830f64c9a9ec23aeb47fad9761c0988a04d51eb68a16d572484',
    'embodiment': 'US12573352B2 Eq5 without optional Eq6/7; not consumer CM selection',
}
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
    absolute = variant == ABSOLUTE_VARIANT
    applied = derived['float'] if variant in SOP_VARIANTS else {'S': 1.0, 'O': 0.0, 'P': 1.0}
    unapplied = [0, 1, 2, 6, 7, 8] if variant in SOP_VARIANTS else list(range(9))
    l1 = meta['l1']
    branch = ('flat-source' if l1['min_pq'] == l1['max_pq'] else
              'collapsed-tail' if l1['min_pq'] == l1['avg_pq'] else
              'collapsed-head' if l1['avg_pq'] == l1['max_pq'] else 'regular')
    result = {'id': ABSOLUTE_ALGORITHM if absolute else ALGORITHM, 'variant': variant,
            'frozen_decisions': ABSOLUTE_DECISIONS if absolute else FROZEN_DECISIONS,
            'domain': ('absolute normalized-PQ; no target normalization; existing HPE-LMS/PQ/IPT I placement'
                       if absolute else 'normalized-PQ; existing HPE-LMS/PQ/IPT I placement'),
            'l1_curve_domain': 'nits rational' if variant == 'l1-rational' else 'normalized-PQ analytic Hermite',
            'l1': l1, 'l1_presence': True, 'degenerate_branch': branch,
            'target': obj['target'], 'target_generation': 1, 'target_description_id': 27,
            'source_records': meta['records'], 'selected_records': selected,
            'original_trim': trims[0], 'derived_factors': derived, 'applied_factors': applied,
            'selected_cm_name': None, 'algorithm_versions': meta['algorithm_versions'],
            'curve_defaults': {'preservation_tail': 0.5, 'preservation_head': 0.5,
                               'cutoff': 0.5, 'contrast': 1, 'tail_power': 2, 'head_power': 4},
            'applied_stages': ['explicit presence-aware L1', 'existing L1 chroma compensation once'] +
                              (['OPEN absolute-PQ SOP'] if absolute else
                               ['OPEN target-normalized PQ SOP'] if variant == 'l1-hermite-sop' else []) +
                              ['existing final physical gamut mapping once'],
            'unapplied_trim_indexes': unapplied,
            'unapplied_trim_values': {str(i): trims[0].split(',')[i] for i in unapplied},
            'unapplied_stages': ['chroma', 'saturation', 'detail', 'L3', 'L8', 'midcontrast',
                                 'CM selection', 'temporal rules', 'target interpolation', 'raw-RPU SOP'],
            'hypotheses': HYPOTHESES, 'full_mapping_complete': False}
    if absolute:
        result['sop_domain'] = 'PL_DOVI_DM_SOP_ABSOLUTE_PQ'
        result['sop_equation'] = 'u=clamp(S*y+O,0,1); output=clamp(pow(u,P),PQ(target.black),PQ(target.peak))'
        result['sop_clamp_policy'] = 'OPEN finite/nonnegative input and physical output-volume clamps; not normative'
    if variant in (RGB_VARIANT, Y_VARIANT, MB_VARIANT):
        from tools.dolby_harness.public_mapping import mpc_prepare
        original = [Fraction(x) for x in trims[0].split(',')]
        if not all(-1 <= original[i] <= 1 for i in (6, 7)):
            raise ValueError('public RGB XML color controls require [-1,1]')
        cw, sg = float(original[6]/2), float(original[7]/2)
        result.update(id='open-continuous-xml-rgb-pq-pre-rational-v1',
            domain='absolute PQ BT2020 RGB SOP/color before linear-nits rational luminance',
            l1_curve_domain='linear BT2020 CIE Y nits; continuous scene L1 anchors',
            prepared_curve=mpc_prepare(tuple(l1[k] for k in ('min_pq','avg_pq','max_pq')), 600),
            color_factors={'cw':cw,'sg':sg,'status':'bypass-neutral-sg' if sg == 0 else 'applied'},
            applied_stages=['linear source-to-BT2020 basis conversion', 'RGB absolute-PQ SOP',
                'public inside-exponent color expression', 'rational luminance once',
                'existing final physical gamut mapping once'],
            unapplied_trim_indexes=[0,1,2,8],
            unapplied_trim_values={str(i):trims[0].split(',')[i] for i in (0,1,2,8)},
            unapplied_stages=['detail','L3','L8','midcontrast','CM selection','temporal rules',
                'target interpolation','raw-RPU SOP'],
            curve_defaults={'min_knee':.1,'max_knee':.8,'default_knee':.4,'adaptation':.4},
            frozen_decisions={'DoViBaker':'ffba39830b694ddca0bf5f73dcf1b462713bb7f4',
                'MPC':'6bb2f3d702993f04e888bf5abd0944a83333b3c5',
                'serializer':'614c816b6446dcd1dbaf433403d499a6026fbb5a',
                'scope':'independent continuous-XML RGB adaptation, not official CM identity'},
            hypotheses=['Continuous XML serializer composition; no raw12 or UINT nits quantization',
                'MPC6 mathematical stage order, not official implementation identity',
                'Negative SOP bases clamp before power; published post-power PQ floor1e-5',
                'Actual scalar/GPU caps post-color PQ at1 as explicit finite physical-domain extension',
                'Target black0 required; singular/flat L1 intervals rejected',
                'CW is present but ineffective when SG is0 under this operator'])
        if variant in (Y_VARIANT, MB_VARIANT):
            if variant == Y_VARIANT and sg != 0:
                raise ValueError('Y-PQ-pre supports exact SG0 only; no RGB fallback')
            if variant == Y_VARIANT and applied['S'] + applied['O'] > 1:
                raise ValueError('Y-PQ-pre SOP exceeds physical PQ domain')
            if variant == MB_VARIANT and applied['S'] * l1['max_pq'] + applied['O'] > 1:
                raise ValueError('mastering-black SOP exceeds PQ1 over declared L1 range')
            result.update(id='open-continuous-xml-y-pq-pre-rational-v1',
                domain='absolute PQ of scalar linear BT2020 Y before rational Y',
                color_factors={'cw':cw,'sg':sg,'status':'supported-SG0-only; CW present/no effect'},
                applied_stages=['linear source-to-BT2020 basis conversion', 'scalar Y absolute-PQ SOP',
                    'rational scalar luminance once', 'restore original linear RGB ratios',
                    'existing final physical gamut mapping once'],
                hypotheses=['W continuous XML serializer/public-decoder composition, not direct XML pixel identity',
                    'Scalar Y extension, not a complete official/patent mapper',
                    'Exact SG0 only; nonzero SG unsupported without fallback',
                    'Zero Y maps to black; nonnegative affine/published post-power PQ floor1e-5',
                    'Full-domain SOP must remain within PQ1; no RGB per-channel trim or stock compensation'])
            if variant == MB_VARIANT:
                from tools.dolby_harness.public_mapping import mpc_mastblack_prepare
                mastering_black = obj['source']['mastering']['min_nits']
                result.update(id='open-y-pq-pre-mastblack-v1',
                    prepared_curve=mpc_mastblack_prepare(
                        tuple(l1[k] for k in ('min_pq','avg_pq','max_pq')), 600, mastering_black),
                    l1_curve_domain='nits rational; lo-forced-0 PQ knee; declared mastering-black anchor',
                    mastering_black_nits=mastering_black,
                    color_factors={'cw':cw,'sg':sg,'status':'bypass-neutral-sg' if sg == 0 else 'applied-after-ratio'},
                    applied_stages=['linear source-to-BT2020 basis conversion', 'scalar Y absolute-PQ SOP',
                        'rational scalar luminance once', 'restore original linear RGB ratios',
                        'public inside-exponent PQ color after ratio', 'existing final physical gamut mapping once'],
                    hypotheses=['W continuous XML serializer/public-decoder composition, not direct XML pixel identity',
                        'lo-forced-0 knee follows pinned MPC CPU UINT-nits minimum truncation',
                        'Declared mastering-black rational anchor follows named shader semantics; not fitted',
                        'Color-after-ratio scalar extension; nonzero SG applied, not substituted',
                        'Zero Y maps to black before color; SOP within PQ1 over declared L1 range',
                        'Scalar per-pixel affine SOP fails closed above PQ1; GPU finite PQ1 cap must be unexercised',
                        'Published 1e-5 post-SOP PQ floor; reject post-color PQ above1, no clipping'])
    if variant == SQRTSUM_VARIANT:
        from tools.dolby_harness import sqrtsum
        original = [Fraction(x) for x in trims[0].split(',')]
        if not all(-1 <= original[i] <= 1 for i in (6, 7)):
            raise ValueError('public XML color controls require [-1,1]')
        source, target = obj['source']['mastering'], obj['target']
        curve = sqrtsum.prepare(tuple(l1[k] for k in ('min_pq','avg_pq','max_pq')),
            source['min_nits'], source['max_nits'], target['min_nits'], target['max_nits'])
        cw, sg = float(original[6]/2), float(original[7]/2)
        result.update(id=sqrtsum.ALGORITHM, protocol='DVH4',
            target_description_id=int(target['id']),
            domain='absolute PQ of original linear BT2020 CIE Y; curve then scalar W SOP',
            l1_curve_domain='absolute PQ powered rational with explicit constant endpoint extension',
            prepared_curve=curve,
            field_provenance={'source_display':'source.mastering original declared min_nits/max_nits',
                'target_display':'original selected target declaration min_nits/max_nits',
                'L1':'original metadata min_pq/avg_pq/max_pq, unaltered',
                'SOP_CW_SG':'original selected Trim continuous W serializer composition'},
            color_factors={'cw':cw,'sg':sg,'status':'bypass-neutral-sg' if sg == 0 else 'applied-after-ratio'},
            curve_defaults={'screen_ratio':1.,'rolloff':1./3.},
            applied_stages=['linear source-to-BT2020 basis conversion', 'original CIE Y absolute PQ',
                'US961 sqrt-sum powered rational', 'scalar W absolute-PQ post-SOP',
                'restore original linear RGB ratios', 'actual PQ CW/SG after ratio',
                'ONE final physical P3 clip'],
            unapplied_trim_indexes=[0,1,2,8],
            unapplied_trim_values={str(i):trims[0].split(',')[i] for i in (0,1,2,8)},
            unapplied_stages=['detail','L3','L8','midcontrast','CM selection','temporal rules',
                'target interpolation','raw-RPU SOP','stock L1 compensation'],
            frozen_decisions={'source':'US9613407B2 paragraphs0048-0062/Table2',
                'source_html_sha256':'dd8584d4b80095d1499e476f4f3cb6b1ee387e9e2c392d9ba89c72add681b511',
                'frozen_contract_sha256':'4deb62586fae800209128174e5555faa56ec43216aacfdf14e83035a319ffbb8',
                'representation':sqrtsum.REPRESENTATION},
            hypotheses=['Open hybrid; no literal complete patent or official CM identity',
                'Constant endpoint saturation is a NONLITERAL engineering extension',
                'Positive-weight powered anchors are algebraically the same rational; finite closure differs',
                'Y==0 exact black/color bypass; no epsilon ratio',
                'SOP max0 affine and postpower1e-5 floor; no PQ1 cap',
                'Negative/nonfinite base, PQ>1, restored/color domain violations reject',
                'GPU invalid-only safe operands with sticky alpha0; RGBA alpha must survive output',
                'XML detail-.75 unresolved/unapplied'])
    # This object is a JSON protocol value, including prepared-curve vectors.
    # Make its transport representation explicit without weakening strict_equal.
    return json.loads(json.dumps(result, allow_nan=False))


def control(obj, meta, variant):
    a = algorithm(obj, meta, variant)
    sq = variant == SQRTSUM_VARIANT
    values = ['DVH4' if sq else 'DVH3', obj['frame']['width'], obj['frame']['height'], 1]
    if sq:
        values += [a['target_description_id']]
    for v in (obj['source']['mastering'], obj['target']):
        values += [v['min_nits'], v['max_nits'], *v['primaries']]
    values += [meta['l1'][k] for k in ('min_pq', 'avg_pq', 'max_pq')]
    values += [VARIANTS.index(variant)] + [a['applied_factors'][k] for k in ('S', 'O', 'P')]
    if variant in (RGB_VARIANT, Y_VARIANT, MB_VARIANT, SQRTSUM_VARIANT):
        values += [a['color_factors'][k] for k in ('cw','sg')]
    return ' '.join(str(x) for x in values) + '\n'


def sqrtsum_gpu_domain(stdout, obj):
    records = [parse_json(line.encode()) for line in stdout.decode().splitlines() if line.startswith('{')]
    expected_config = {'protocol':'DVH4', 'target_description_id':int(obj['target']['id']),
        'RGBA_components':4, 'independent_alpha':True, 'background':'skip',
        'background_transparency':1, 'blend':False, 'tiles':False, 'hooks':0,
        'lut':False, 'distortion':False}
    population = obj['frame']['width'] * obj['frame']['height']
    expected_domain = {'schema':'hdr.sqrtsum.gpu-domain.v1','population':population,
        'valid':population,'invalid':0,'channel':'downloaded-RGBA-alpha-exact1'}
    if not am.strict_equal(records,[expected_config,expected_domain]):
        raise ValueError('GPU whole-raster domain/config validity receipt mismatch')
    return records[1]


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
        domain = sqrtsum_gpu_domain((stage / 'native.stdout').read_bytes(),obj) if variant == SQRTSUM_VARIANT else None
        result = {'schema': SCHEMA, 'role': 'candidate', 'source_alignment': alignment(obj, meta),
                  'encoding': ENCODING, 'algorithm': algo,
                  'output': {'file': 'output.f32', 'sha256': sha(pixels)},
                  'provenance': {'input_manifest': {'file': str(Path(manifest).resolve()), 'sha256': sha(raw)},
                                 'execution': binding, 'protocol': 'DVH4' if variant == SQRTSUM_VARIANT else 'DVH3',
                                 'control_sha256': prov.sha(stage / 'control.txt'),
                                 'stdout_sha256': prov.sha(stage / 'native.stdout'),
                                 'stderr_sha256': prov.sha(stage / 'native.stderr'),
                                 'target': obj['target'], 'target_generation': 1, 'target_description_id': 27}}
        if domain is not None:
            result['provenance']['gpu_domain'] = domain
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
    if p['protocol'] != ('DVH4' if variant == SQRTSUM_VARIANT else 'DVH3') or native_control != control(obj, meta, variant).encode():
        raise ValueError('OPEN native protocol mismatch')
    for name in ('stdout', 'stderr'):
        am.snapshot(path.parent, {'file': 'native.' + name, 'sha256': p[name + '_sha256']})
    if variant == SQRTSUM_VARIANT:
        domain = sqrtsum_gpu_domain((path.parent / 'native.stdout').read_bytes(),obj)
        if not am.strict_equal(p.get('gpu_domain'),domain):
            raise ValueError('GPU whole-raster domain record differs from native download')
    normalized = am.output_snapshot(path.parent, r['output'], obj['frame']['width'], obj['frame']['height'])
    return r, am.pixel_samples(normalized)


def compare(candidate, reference):
    from tools.dolby_harness.open_dm_provenance import implementation
    candidate_raw = read_bounded(candidate, 4 * 1024 * 1024)
    a, pa = validate_result(candidate, candidate_raw)
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
            'candidate_manifest_sha256': sha(candidate_raw),
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
