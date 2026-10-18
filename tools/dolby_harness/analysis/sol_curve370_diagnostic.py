"""Once-only US961 sqrt-sum PQ-Y hybrid; see sol_curve370_contract.txt.

No preflight/baseline execution. Only retained development lattices256/714.
Python -B -I execution freezes all inputs before the only new population runs.
"""
import collections
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent
sys.path.insert(0, str(HERE))
import fable_eval as f

NAME = 'us961-sqrtsum-pq-y-post-v1'
PREFLIGHT = ROOT / 'scratch370/source-curve-preflight.json'
PREFLIGHT_SHA = 'a351b04fb26a634877611313ebe8626f36a728bdf5989704b97fdc4bfc636166'
CONTRACT = HERE / 'sol_curve370_contract.txt'
OUT = ROOT / 'sol-curve370'
ORIGINAL_STRATA = f.strata_key
ORIGINAL_CLIP = f.final_clip


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, doc):
    with Path(path).open('x') as stream:
        json.dump(doc, stream, indent=2, allow_nan=False)
        stream.write('\n')


def canonical(doc):
    return json.loads(json.dumps(doc, allow_nan=False))


def closure():
    paths = {Path(__file__).resolve(), CONTRACT}
    for module in tuple(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file:
            path = Path(file).resolve()
            if path.is_relative_to(REPO) and path.suffix == '.py':
                paths.add(path)
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def prepare(meta, expected):
    """Direct Table2 preparation only; never import/execute old preflight."""
    smin, smax = (f.pq_inverse(v) for v in (.005, 4000.))
    tmin, tmax = (f.pq_inverse(v) for v in (0., meta['peak']))
    crush, mid, clip = meta['l1']
    ratio = min(1., math.sqrt((tmax + tmin) / (smax + smin)))
    screen_ratio, rolloff = 1., 1. / 3.
    slope = math.sqrt(1. / ratio) * screen_ratio
    key = 2. * (mid - crush) / (clip - crush)
    shift = mid * (1. - ratio) * key * screen_ratio
    xs = (crush, mid, clip)
    ys = (max(crush - shift, tmin), mid - shift, min(clip - shift, tmax))
    n = slope / rolloff
    xx, yy = [v ** n for v in xs], [v ** (1. / rolloff) for v in ys]
    co = f.pm.solve3([(1., x, -x*y) for x, y in zip(xx, yy)], yy)
    prepared = dict(ratio=ratio, slope=slope, screen_ratio=screen_ratio, key=key,
                    shift=shift, rolloff=rolloff, n=n, source_anchors=xs,
                    target_anchors=ys, coefficients=co)
    for field, value in prepared.items():
        assert canonical(value) == expected[field], 'preflight mismatch: ' + field
    assert 0 <= xs[0] < xs[1] < xs[2] <= 1
    assert 0 <= ys[0] < ys[1] < ys[2] <= 1
    assert n > 0 and rolloff > 0
    # z=q^n and the outer positive power are increasing. The rational
    # derivative in z is (b-a*c)/(1+c*z)^2; its affine denominator and
    # numerator extrema occur at endpoints. Exact fractions prevent a
    # cancellation-prone lower-anchor sign test from becoming a repair.
    a, b, c = map(Fraction, co)
    zlo, zhi = map(Fraction, (xx[0], xx[2]))
    determinant = b - a*c
    denominators = [1+c*z for z in (zlo, zhi)]
    numerators = [a+b*z for z in (zlo, zhi)]
    assert determinant > 0 and min(denominators) > 0 and min(numerators) >= 0
    residuals = [f.pm.rational_eval(co, x) ** rolloff - y for x, y in zip(xx, ys)]
    assert residuals == expected['anchor_residuals']
    assert max(abs(v) for v in residuals) < 1e-10
    proof = {'preflight_preparation_exact_match': True,
             'supported_PQ_interval': xs[::2], 'powered_interval': (xx[0], xx[2]),
             'derivative_determinant_positive_exact': determinant > 0,
             'denominator_endpoint_positive_exact': [v > 0 for v in denominators],
             'numerator_endpoint_nonnegative_exact': [v >= 0 for v in numerators],
             'derivative_determinant': float(determinant),
             'denominator_endpoints': list(map(float, denominators)),
             'numerator_endpoints': list(map(float, numerators)),
             'binary64_anchor_residuals_PQ': residuals,
             'continuity': 'Constant endpoint extension of the anchor-interpolating analytic curve; '
                           'finite binary64 coefficient closure residuals reported, not repaired.',
             'exact_binary_coefficient_rationals': [str(v) for v in (a, b, c)],
             'literal_full_domain_nonnegative_inherited': expected['full_domain_nonnegative'],
             'literal_preflight_invalid_rows_inherited': [r for r in expected['rows'] if not r['valid']]}
    return prepared, proof


def extended_curve(q, curve, counters):
    if not math.isfinite(q) or not 0 <= q <= 1:
        raise ValueError('automatic input outside physical PQ domain')
    lo, _, hi = curve['source_anchors']
    if q <= lo:
        counters['input_q_at_or_below_Crush_pixels'] += 1
        return curve['target_anchors'][0]
    if q >= hi:
        counters['input_q_at_or_above_Clip_pixels'] += 1
        return curve['target_anchors'][2]
    counters['automatic_interior_pixels'] += 1
    base = f.pm.rational_eval(curve['coefficients'], q ** curve['n'])
    if not math.isfinite(base) or base < 0:
        raise ValueError('negative/nonfinite automatic interior fractional-power base')
    mapped = base ** curve['rolloff']
    if not math.isfinite(mapped) or not 0 <= mapped <= 1:
        raise ValueError('automatic output outside physical PQ domain')
    return mapped


def extended_strata(ref_lin, ry):
    group, luminance = ORIGINAL_STRATA(ref_lin, ry)
    spread = (max(ref_lin)-min(ref_lin))/max(ref_lin) if max(ref_lin) else None
    original = ('black' if spread is None else 'nonblack-neutral' if spread <= .01 and ry >= .01
                else 'nearblack-neutral' if spread <= .01 else 'chroma')
    return group, luminance, 'original/'+original, 'original/'+original+'/'+luminance


COUNTERS = ('source_Y_zero_pixels', 'input_q_at_or_below_Crush_pixels',
            'input_q_at_or_above_Clip_pixels', 'automatic_interior_pixels',
            'sop_affine_negative_pixels', 'sop_affine_zero_pixels', 'sop_power_floor_pixels',
            'zero_Y_colour_bypass_pixels', 'raw_source_BT2020_negative_pixels',
            'restored_BT2020_negative_pixels', 'raw_BT2020_negative_pixels',
            'physical_P3_negative_pixels', 'physical_P3_above600_pixels',
            'physical_P3_negative_channels', 'physical_P3_above600_channels',
            'domain_failure_pixels')


def evaluate_once(rows, meta, curve, stage):
    seen = collections.Counter()
    outputs, ranges = [], {}

    def observe(key, values):
        if not all(math.isfinite(v) for v in values):
            raise ValueError('nonfinite ' + key)
        bounds = ranges.setdefault(key, [min(values), max(values)])
        bounds[0], bounds[1] = min(bounds[0], min(values)), max(bounds[1], max(values))

    def chain(rgb, metadata, prepared, counters):
        """US961 PQ-Y curve + explicit endpoint saturation -> W SOP -> ratio RGB -> actual CW/SG."""
        seen['chain_calls'] += 1
        outputs.append({'xy': rows[len(outputs)][0]})
        for key in COUNTERS:
            counters[key] += 0
        step = 'source'
        try:
            counters['raw_source_BT2020_negative_pixels'] += min(rgb) < 0
            y = f.lum(rgb)
            observe('source_Y_nits', (y,))
            q = f.pq_inverse(y)
            counters['source_Y_zero_pixels'] += y == 0
            step = 'automatic'
            mapped_q = extended_curve(q, prepared['automatic'], counters)
            observe('automatic_output_PQ', (mapped_q,))
            step = 'scalar_SOP'
            s, o, p = metadata['sop']
            affine = s * mapped_q + o
            counters['sop_affine_negative_pixels'] += affine < 0
            counters['sop_affine_zero_pixels'] += affine == 0
            power = max(0., affine) ** p
            counters['sop_power_floor_pixels'] += power < 1e-5
            trimmed_q = f.sop_pq(mapped_q, metadata['sop'])
            observe('post_SOP_PQ', (trimmed_q,))
            if not 0 <= trimmed_q <= 1:
                raise ValueError('scalar SOP outside physical PQ domain')
            mapped_y = f.pq_eotf(trimmed_q)
            step = 'ratio_restoration'
            restored = tuple(v * mapped_y / y for v in rgb) if y else (0., 0., 0.)
            counters['restored_BT2020_negative_pixels'] += min(restored) < 0
            observe('restored_BT2020_nits', restored)
            if any(not 0 <= v <= 10000 for v in restored):
                raise ValueError('restored RGB outside physical PQ domain')
            step = 'post_ratio_colour'
            if y == 0:
                counters['zero_Y_colour_bypass_pixels'] += 1
                mapped = (0., 0., 0.)
            else:
                mapped = f._colour_only(restored, metadata)
                seen['actual_colour_calls'] += 1
            counters['raw_BT2020_negative_pixels'] += min(mapped) < 0
            observe('post_colour_BT2020_nits', mapped)
            if any(not 0 <= v <= 10000 for v in mapped):
                raise ValueError('post-colour RGB outside physical PQ domain')
            native = f.pm.apply_matrix(f.TO_P3, mapped)
            observe('preclip_physical_P3_nits', native)
            counters['physical_P3_negative_pixels'] += min(native) < 0
            counters['physical_P3_above600_pixels'] += max(native) > metadata['peak']
            counters['physical_P3_negative_channels'] += sum(v < 0 for v in native)
            counters['physical_P3_above600_channels'] += sum(v > metadata['peak'] for v in native)
            outputs[-1].update(automatic_PQ=mapped_q, post_SOP_PQ=trimmed_q,
                               raw_BT2020_nits=mapped, raw_physical_P3_nits=native)
            return mapped
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            counters['domain_failure_pixels'] += 1
            counters['domain_failure_stage_'+step] += 1
            outputs[-1].update(invalid=str(exc), failure_stage=step)
            raise

    def clip_once(rgb, peak):
        seen['final_P3_clip_calls'] += 1
        clipped, excursion = ORIGINAL_CLIP(rgb, peak)
        observe('final_BT2020_nits', clipped)
        outputs[-1]['final_BT2020_nits'] = clipped
        return clipped, excursion

    f.prep = lambda metadata: {'automatic': curve}
    f.CHAINS[NAME] = chain
    f.strata_key, f.final_clip = extended_strata, clip_once
    result = f.evaluate(rows, meta, NAME)  # Only new-chain population evaluation.
    assert seen['chain_calls'] == len(rows) == len(outputs)
    assert seen['final_P3_clip_calls'] == result['valid']
    assert sum(result['invalid'].values()) == result['counters']['domain_failure_pixels']
    c = result['counters']
    assert (c['automatic_interior_pixels'] + c['input_q_at_or_below_Crush_pixels'] +
            c['input_q_at_or_above_Clip_pixels']) <= len(rows)
    complete = result['valid'] == result['population'] and not result['invalid']
    final, raw = result.pop('final_clip_all_sample'), result.pop('raw_all_sample')
    result['primary_all_population'] = final if complete else None
    result['partial_final_diagnostic'] = None if complete else final
    raw_complete = complete and not c.get('raw_outside_PQ_domain_pixels', 0)
    result['raw_all_population'] = raw if raw_complete else None
    result['partial_raw_diagnostic'] = None if raw_complete else raw
    result['pass_mean1_p953_sampled_only'] = bool(complete and final['mean'] <= 1 and final['p95'] <= 3)
    result['disposition'] = ('REPORT_TO_COORDINATOR_NO_PROMOTION' if result['pass_mean1_p953_sampled_only']
                             else 'REJECT_STOP_NO_VARIANTS')
    result['execution_counts'], result['output_ranges'] = dict(seen), ranges
    result['strata_note'] = ('Reference-Y bins are disjoint with upper edges .01,.1,1,10,100,600; '
                            'above600 means >=600. Original four groups and cross cells retained. '
                            'Source-Y halfdecades use original unchanged adapter.')
    assert sum(v['pixels'] for k, v in result['final_clip_strata'].items()
               if k.startswith('original/') and k.count('/') == 1) == result['valid']
    assert sum(v['pixels'] for k, v in result['final_clip_strata'].items()
               if k.startswith('refY<')) == result['valid']
    save(stage / 'lattice-output.json', outputs)
    result['lattice_output_sha256'] = sha(stage / 'lattice-output.json')
    return result


def main():
    started = time.time()
    assert len(sys.argv) == 1, 'no arguments; fixed development shots only'
    assert not os.environ.get('FABLE_L1'), 'metadata override forbidden'
    assert Path(f.EVIDENCE).resolve() == ROOT, 'evidence override forbidden'
    assert sha(PREFLIGHT) == PREFLIGHT_SHA
    preflight = json.loads(PREFLIGHT.read_bytes())
    for rel, digest in preflight['source_hashes'].items():
        assert sha(ROOT / rel) == digest, 'retained preflight dependency changed: ' + rel
    loaded, provenance = {}, {}
    for shot in ('256', '714'):
        path, digest, rows, meta = f.load(shot)
        expected = preflight['shots'][shot]
        driver_path = ROOT / ('fable_eval_'+shot+'_driver.json')
        driver = json.loads(driver_path.read_bytes())
        assert sha(driver_path) == expected['metadata_receipt_sha256']
        assert digest == driver['input_sha256']
        assert canonical(meta) == driver['meta'] == expected['metadata']
        assert len(rows) == 34560
        assert [xy for xy, src, ref in rows] == [(x, y) for y in range(0, 2160, 16)
                                               for x in range(0, 4096, 16)]
        assert meta['peak'] == 600. and (shot != '714' or meta['color'][1] != 0.)
        curve, proof = prepare(meta, expected)
        reference_path = ROOT / f'evidence355/native/mastblack347/{shot}/reference-rebound355.json'
        reference = json.loads(reference_path.read_bytes())
        align = reference['alignment']
        assert align['frame_index'] == int(shot)
        assert align['source']['mastering']['min_nits'] == .005
        assert align['source']['mastering']['max_nits'] == 4000.
        assert align['target']['min_nits'] == 0 and align['target']['max_nits'] == 600.
        input_doc = json.loads(Path(path).read_bytes())
        if shot == '714':
            assert input_doc['frame']['input']['sha256'] == align['source_sha256']
        provenance[shot] = dict(input_path=str(path), input_sha256=digest,
            metadata_driver_path=str(driver_path), metadata_driver_sha256=sha(driver_path),
            metadata=meta, prepared=curve, preparation_proof=proof,
            original_cache_identity=input_doc['cache'], reference_manifest_path=str(reference_path),
            reference_manifest_sha256=sha(reference_path),
            inherited_original_source_sha256=align['source_sha256'],
            inherited_original_reference_sha256=reference['output']['sha256'],
            original_hash_qualification='Inherited manifest raster hashes, not reread/rendered original rasters. '
                                        'Evaluated lattice bytes hashed directly.256 reconstruction unchanged.')
        loaded[shot] = rows, meta, curve
    sources = closure()
    OUT.mkdir(exist_ok=True)
    frozen_path = OUT / 'FROZEN.json'
    frozen = dict(schema='hdr.sol370.curve.freeze.v1', variant=NAME,
        preflight_sha256=PREFLIGHT_SHA, script_sha256=sha(__file__), contract_sha256=sha(CONTRACT),
        repository_import_closure_sha256=sources, retained_source_hashes=preflight['source_hashes'],
        python=sys.version, platform=platform.platform(), shots=provenance,
        scope='source-grounded hybrid with NONLITERAL endpoint extension; not complete patent/CM2.9 identity',
        metric='unchanged BT2124 deltaEITP; nearest-rank p95; thresholds mean<=1 AND p95<=3',
        source_detail_minus075='unresolved/unapplied', baseline_evaluations=0,
        preflight_executions=0, native_requests=0, renders=0, units=0, holdout_access=False)
    save(frozen_path, frozen)  # Exclusive once-only guard and freeze BEFORE any pixels.
    print('FROZEN_SHA256', sha(frozen_path), flush=True)
    report: dict[str, Any] = dict(schema='hdr.sol370.curve.result.v1',
                                  frozen_sha256=sha(frozen_path), shots={})
    for shot, (rows, meta, curve) in loaded.items():
        assert closure() == sources
        assert sha(provenance[shot]['input_path']) == provenance[shot]['input_sha256']
        stage = OUT / shot
        stage.mkdir(exist_ok=False)
        save(stage / 'STARTED.json', dict(shot=shot, candidate_executions_authorized=1,
                                       frozen_sha256=report['frozen_sha256']))
        result = evaluate_once(rows, meta, curve, stage)
        assert closure() == sources
        save(stage / 'RESULT.json', result)
        report['shots'][shot] = dict(result_sha256=sha(stage / 'RESULT.json'),
            lattice_output_sha256=result['lattice_output_sha256'],
            primary_all_population=result['primary_all_population'], invalid=result['invalid'],
            counters=result['counters'], population=result['population'], valid=result['valid'],
            pass_mean1_p953_sampled_only=result['pass_mean1_p953_sampled_only'],
            disposition=result['disposition'], candidate_executions=1)
        print(shot, json.dumps(report['shots'][shot], allow_nan=False), flush=True)
    report['disposition'] = ('REPORT_TO_COORDINATOR_NO_PROMOTION' if all(
        r['pass_mean1_p953_sampled_only'] for r in report['shots'].values()) else 'REJECT_STOP_NO_VARIANTS')
    report['seconds'], report['no_final_accuracy_claim'] = time.time()-started, True
    save(OUT / 'RESULTS.json', report)
    print('RESULTS_SHA256', sha(OUT / 'RESULTS.json'), flush=True)


if __name__ == '__main__':
    main()
