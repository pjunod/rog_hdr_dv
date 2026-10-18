"""Once-only retained-lattice diagnostic of Astra362's frozen endpoint hybrid.

No renderer, baseline execution, parameter selection or holdout access. Imports
Astra's preparation unchanged and checks it against its retained preflight before
mapping any pixel. Uses fable_eval's loader, evaluator, metric and final P3 clip.
Run from any directory: python3 -B -I sol362_display_endpoints.py
Private receipts go to the enclosing workspace's sol-eval362/ (exclusive create).
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent
sys.path.insert(0, str(HERE))
import astra362_display_endpoints as astra

f = astra.f
NAME = 'display-endpoints-content-knee-constant04-w-pre-sop-post-ratio-colour'
PREFLIGHT_SHA256 = '5c4c021e4dedc928ebdc0466545c80769b2647365831f1b1f135bad922a0db23'
PREPARATION_SHA256 = '69814d1f95b9a2dabf9c07d04681aff5baa094e70b8d5426dd7fcf096729df4e'
ADAPTER_SHA256 = '77bf770b08739f62181b981c2d225e6ebd32a02a60430994453582963de4a274'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, doc):
    with Path(path).open('x') as stream:
        json.dump(doc, stream, indent=2, allow_nan=False)
        stream.write('\n')


def canonical(doc):
    return json.loads(json.dumps(doc, allow_nan=False))


def import_closure():
    paths = {Path(__file__).resolve()}
    for module in tuple(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file:
            path = Path(file).resolve()
            if path.is_relative_to(REPO) and path.suffix == '.py':
                paths.add(path)
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(paths)}


def extend_strata(ref_lin, ry):
    """Keep adapter strata; add original four groups and their disjoint Y cells."""
    group, luminance = ORIGINAL_STRATA(ref_lin, ry)
    spread = (max(ref_lin) - min(ref_lin)) / max(ref_lin) if max(ref_lin) else None
    original = ('black' if spread is None else 'nonblack-neutral' if spread <= .01 and ry >= .01
                else 'nearblack-neutral' if spread <= .01 else 'chroma')
    return group, luminance, 'original/' + original, 'original/' + original + '/' + luminance


ORIGINAL_STRATA = f.strata_key
ORIGINAL_CLIP = f.final_clip


def evaluate_once(rows, meta, curve, stage):
    counters_seen = collections.Counter()
    outputs = []
    ranges = {}

    def observe(key, values):
        if not all(math.isfinite(v) for v in values):
            raise ValueError('nonfinite ' + key)
        bounds = ranges.setdefault(key, [min(values), max(values)])
        bounds[0] = min(bounds[0], min(values))
        bounds[1] = max(bounds[1], max(values))

    def chain(rgb, metadata, prepared, counters):
        """W absolute-PQ scalar SOP -> frozen nits rational -> RGB/Y ratio -> actual PQ CW/SG."""
        for key in ('source_Y_zero_pixels', 'sop_affine_negative_pixels', 'sop_power_floor_pixels',
                    'rational_negative_clamp_pixels', 'physical_P3_negative_pixels',
                    'physical_P3_above600_pixels', 'physical_P3_negative_channels',
                    'physical_P3_above600_channels', 'raw_BT2020_negative_pixels'):
            counters[key] += 0
        counters_seen['chain_calls'] += 1
        outputs.append({'xy': rows[len(outputs)][0]})
        y = f.lum(rgb)
        observe('source_Y_nits', (y,))
        counters['source_Y_zero_pixels'] += y == 0
        if y == 0:
            restored = (0., 0., 0.)
        else:
            s, o, p = metadata['sop']
            affine = s * f.pq_inverse(y) + o
            counters['sop_affine_negative_pixels'] += affine < 0
            power = max(0., affine) ** p
            counters['sop_power_floor_pixels'] += power < 1e-5
            trimmed_q = max(1e-5, power)
            if not math.isfinite(trimmed_q) or trimmed_q > 1:
                raise ValueError('scalar SOP outside physical PQ domain')
            trimmed_y = f.pq_eotf(trimmed_q)
            raw_y = f.pm.rational_eval(prepared['display_endpoints']['coefficients'], trimmed_y)
            counters['rational_negative_clamp_pixels'] += raw_y < 0
            mapped_y = max(0., raw_y)
            restored = tuple(v * mapped_y / y for v in rgb)
        observe('restored_BT2020_nits', restored)
        if any(not 0 <= v <= 10000 for v in restored):
            raise ValueError('restored RGB outside physical PQ domain')
        # Unchanged adapter colour expression, including the actual nonzero SG714.
        mapped = f._colour_only(restored, metadata)
        observe('post_colour_BT2020_nits', mapped)
        observe('post_colour_PQ', tuple(f.pq_inverse(v) for v in mapped))
        counters['raw_BT2020_negative_pixels'] += min(mapped) < 0
        native = f.pm.apply_matrix(f.TO_P3, mapped)
        observe('preclip_physical_P3_nits', native)
        counters['physical_P3_negative_pixels'] += min(native) < 0
        counters['physical_P3_above600_pixels'] += max(native) > metadata['peak']
        counters['physical_P3_negative_channels'] += sum(v < 0 for v in native)
        counters['physical_P3_above600_channels'] += sum(v > metadata['peak'] for v in native)
        outputs[-1]['raw_BT2020_nits'] = mapped
        return mapped

    def clip_once(rgb, peak):
        counters_seen['final_P3_clip_calls'] += 1
        clipped, excursion = ORIGINAL_CLIP(rgb, peak)
        observe('final_BT2020_nits', clipped)
        outputs[-1]['final_BT2020_nits'] = clipped
        return clipped, excursion

    f.prep = lambda metadata: {'display_endpoints': curve}
    f.CHAINS[NAME] = chain
    f.strata_key = extend_strata
    f.final_clip = clip_once
    # The only population evaluation. Baselines/preflight probes are not invoked.
    result = f.evaluate(rows, meta, NAME)
    assert counters_seen['chain_calls'] == len(rows)
    assert counters_seen['final_P3_clip_calls'] == result['valid']
    complete = result['valid'] == result['population'] and not result['invalid']
    final = result.pop('final_clip_all_sample')
    raw = result.pop('raw_all_sample')
    result['primary_all_population'] = final if complete else None
    result['partial_final_diagnostic'] = None if complete else final
    raw_complete = complete and not result['counters'].get('raw_outside_PQ_domain_pixels', 0)
    result['raw_all_population'] = raw if raw_complete else None
    result['partial_raw_diagnostic'] = None if raw_complete else raw
    result['pass_mean1_p953_sampled_only'] = bool(complete and final['mean'] <= 1 and final['p95'] <= 3)
    result['disposition'] = ('REPORT_TO_COORDINATOR_NO_PROMOTION' if result['pass_mean1_p953_sampled_only']
                             else 'REJECT_STOP_NO_VARIANTS')
    result['execution_counts'] = dict(counters_seen)
    result['output_ranges'] = ranges
    result['strata_interval_note'] = ('refY< labels are disjoint ascending bins with lower bound equal to '
                                    'the previous upper edge; upper edges .01,.1,1,10,100,600; '
                                    'above600 includes >=600. Original groups and cross cells retained.')
    for prefix in ('original/',):
        group_count = sum(v['pixels'] for k, v in result['final_clip_strata'].items()
                          if k.startswith(prefix) and k.count('/') == 1)
        assert group_count == result['valid']
    assert sum(v['pixels'] for k, v in result['final_clip_strata'].items()
               if k.startswith('refY<')) == result['valid']
    save(stage / 'lattice-output.json', outputs)
    result['lattice_output_sha256'] = sha(stage / 'lattice-output.json')
    return result


def main():
    started = time.time()
    if len(sys.argv) != 1:
        raise ValueError('no arguments; only frozen development shots256/714 are supported')
    if os.environ.get('FABLE_L1') or (os.environ.get('FABLE_EVIDENCE_DIR') and
                                    Path(os.environ['FABLE_EVIDENCE_DIR']).resolve() != ROOT):
        raise ValueError('metadata/evidence environment overrides prohibited')
    assert Path(f.EVIDENCE).resolve() == ROOT
    preflight_path = ROOT / 'scratch362/display-endpoints-preflight.json'
    assert sha(preflight_path) == PREFLIGHT_SHA256
    preflight = json.loads(preflight_path.read_bytes())
    assert sha(astra.__file__) == PREPARATION_SHA256 == preflight['script_sha256']
    assert sha(f.__file__) == ADAPTER_SHA256 == preflight['adapter_sha256']
    closure = import_closure()
    loaded = {}
    provenance = {}
    for shot in ('256', '714'):
        path, digest, rows, meta = f.load(shot)
        driver_path = ROOT / ('fable_eval_' + shot + '_driver.json')
        driver = json.loads(driver_path.read_bytes())
        expected = preflight['shots'][shot]
        assert sha(driver_path) == expected['metadata_receipt_sha256']
        assert digest == driver['input_sha256']
        assert canonical(meta) == driver['meta'] == expected['metadata']
        assert len(rows) == 34560
        assert [xy for xy, src, ref in rows] == [(x, y) for y in range(0, 2160, 16)
                                               for x in range(0, 4096, 16)]
        curve = astra.prepare(meta)
        assert canonical(curve) == expected['curve'], 'preparation mismatch: STOP, no tuning'
        assert meta['peak'] == 600. and (shot != '714' or meta['color'][1] != 0.)
        reference_path = ROOT / f'evidence355/native/mastblack347/{shot}/reference-rebound355.json'
        reference = json.loads(reference_path.read_bytes())
        assert reference['alignment']['frame_index'] == int(shot)
        assert reference['alignment']['source']['mastering']['min_nits'] == .005
        assert reference['alignment']['source']['mastering']['max_nits'] == 4000
        assert reference['alignment']['target']['min_nits'] == 0
        assert reference['alignment']['target']['max_nits'] == meta['peak']
        input_doc = json.loads(Path(path).read_bytes())
        if shot == '714':
            assert input_doc['frame']['input']['sha256'] == reference['alignment']['source_sha256']
        provenance[shot] = {'input_path': str(path), 'input_sha256': digest,
            'metadata_driver_path': str(driver_path), 'metadata_driver_sha256': sha(driver_path),
            'metadata': meta, 'prepared': curve, 'preflight_preparation_exact_match': True,
            'original_cache_identity': input_doc['cache'],
            'reference_manifest_path': str(reference_path), 'reference_manifest_sha256': sha(reference_path),
            'inherited_original_source_sha256': reference['alignment']['source_sha256'],
            'inherited_original_reference_sha256': reference['output']['sha256'],
            'original_hash_qualification': 'Inherited manifest identities, NOT reread/rendered original binary rasters; '
                                           'actual evaluated lattice input bytes hashed above.256 source reconstruction unchanged.'}
        loaded[shot] = rows, meta, curve
    output = ROOT / 'sol-eval362'
    output.mkdir(exist_ok=False)  # Once-only marker: never retry a pixel execution.
    frozen = {'schema': 'hdr.sol362.display-endpoints.freeze.v1',
        'variant': NAME, 'preflight_sha256': PREFLIGHT_SHA256, 'script_sha256': sha(__file__),
        'repository_import_closure_sha256': closure, 'python': sys.version, 'platform': platform.platform(),
        'metric': 'unchanged BT.2124 deltaEITP; nearest-rank p95; signed components720*(candidate-reference)',
        'scope': 'sampled new hybrid diagnostic only; not literal MPC, official pipeline or final accuracy acceptance',
        'native_requests': 0, 'builds': 0, 'units': 0, 'renders': 0, 'baseline_evaluations': 0,
        'holdout_access': False, 'shots': provenance}
    save(output / 'FROZEN.json', frozen)
    report = {'schema': 'hdr.sol362.display-endpoints.result.v1',
        'frozen_sha256': sha(output / 'FROZEN.json'), 'shots': {}}
    for shot, (rows, meta, curve) in loaded.items():
        assert import_closure() == closure, 'import source changed during diagnostic'
        assert sha(provenance[shot]['input_path']) == provenance[shot]['input_sha256']
        stage = output / shot
        stage.mkdir(exist_ok=False)
        save(stage / 'STARTED.json', {'shot': shot, 'candidate_executions_authorized': 1,
                                    'frozen_sha256': report['frozen_sha256']})
        result = evaluate_once(rows, meta, curve, stage)
        assert import_closure() == closure
        save(stage / 'RESULT.json', result)
        report['shots'][shot] = {'result_sha256': sha(stage / 'RESULT.json'),
            'lattice_output_sha256': result['lattice_output_sha256'],
            'primary_all_population': result['primary_all_population'], 'invalid': result['invalid'],
            'counters': result['counters'], 'population': result['population'], 'valid': result['valid'],
            'pass_mean1_p953_sampled_only': result['pass_mean1_p953_sampled_only'],
            'disposition': result['disposition'], 'candidate_executions': 1}
        print(shot, json.dumps(report['shots'][shot]), flush=True)
    report['disposition'] = ('REPORT_TO_COORDINATOR_NO_PROMOTION' if all(
        r['pass_mean1_p953_sampled_only'] for r in report['shots'].values()) else 'REJECT_STOP_NO_VARIANTS')
    report['seconds'] = time.time() - started
    report['no_final_accuracy_claim'] = True
    save(output / 'RESULTS.json', report)
    print('RESULTS_SHA256', sha(output / 'RESULTS.json'), flush=True)


if __name__ == '__main__':
    main()
