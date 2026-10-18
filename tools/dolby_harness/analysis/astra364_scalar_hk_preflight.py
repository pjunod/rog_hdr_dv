"""Synthetic-only scalar-SOP/HK placement preflight; no development pixels.

Compare one declared hybrid against the prior RGB-pre/HK chain on synthetic
P3 rays. Actual CW/SG first, Ebner/PQ/IPT, HK forward, scalar SOP(K), retained
MB curve, exact HK inverse with original normalized chroma, inverse colour.
No new parameters; this is not a literal patent or official runtime contract.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astra360_hk as old

f, pm, ip, hk = old.f, old.pm, old.ip, old.hk


def chain(rgb, meta, prepared, counters):
    coloured = f._colour_only(rgb, meta)
    lms = pm.apply_matrix(ip.RGB_TO_LMS, coloured)
    if not all(math.isfinite(v) and 0 <= v <= 10000 for v in lms):
        raise ValueError('forward LMS outside PQ domain')
    signal = pm.apply_matrix(ip.LMS_TO_IPT, tuple(f.pq_inverse(v) for v in lms))
    k, pn, tn = hk.forward(*signal)
    s, o, p = meta['sop']
    base = s * k + o
    counters['scalar_affine_negative'] += base < 0
    qt = max(1e-5, max(0., base) ** p)
    if not math.isfinite(qt) or qt > 1:
        raise ValueError('trimmed scalar HK outside PQ domain')
    cv = prepared['g_mast_mob'][1]
    raw = pm.rational_eval(cv['coefficients'], f.pq_eotf(qt))
    counters['rational_below_black'] += raw < 0
    mapped = max(0., raw)
    if not math.isfinite(mapped) or mapped > 10000:
        raise ValueError('mapped HK outside PQ domain')
    output_signal = hk.inverse(f.pq_inverse(mapped), pn, tn)
    if not all(math.isfinite(v) for v in output_signal) or not 0 <= output_signal[0] <= 1:
        raise ValueError('inverse HK intensity outside unit domain')
    output = pm.apply_matrix(ip.IPT_TO_LMS, output_signal)
    if not all(math.isfinite(v) and v <= 1 for v in output):
        raise ValueError('inverse LMS-PQ outside upper domain')
    black = f.pq_inverse(0)
    counters['inverse_LMS_below_black_channels'] += sum(v < black for v in output)
    result = pm.apply_matrix(ip.LMS_TO_RGB,
                            tuple(f.pq_eotf(max(black, v)) for v in output))
    if not all(math.isfinite(v) for v in result):
        raise ValueError('nonfinite inverse RGB')
    counters['raw_negative_pixels'] += min(result) < 0
    return result


def main():
    root, out = map(Path, sys.argv[1:])
    if out.exists():
        raise FileExistsError('Retained receipt exists')
    rays = {'neutral': (1., 1., 1.), 'red': (1., .1, .1),
            'green': (.1, 1., .1), 'blue': (.1, .1, 1.),
            'yellow': (1., 1., .1), 'cyan': (.1, 1., 1.),
            'magenta': (1., .1, 1.)}
    identities = {}
    for module in (old, ip, hk, f, pm):
        source_file = module.__file__
        if source_file is None:
            raise ValueError('Import source identity unavailable')
        source_path = Path(source_file)
        identities[source_path.name] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    report = {'schema': 'hdr.astra364.scalar-hk-preflight.v1',
              'scope': 'synthetic colours only; not measured accuracy',
              'source_sha256': identities,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'development_pixels_read': False, 'holdout_access': False,
              'native_requests': 0, 'renders': 0, 'units': 0, 'shots': {}}
    for shot in ('256', '714'):
        raw = (root / ('fable_eval_' + shot + '_driver.json')).read_bytes()
        meta = json.loads(raw)['meta']
        prepared = {'g_mast_mob': f.grid_curve(meta['l1'], meta['peak'], 'mast', 'mob')}
        rows = []
        for source_y in (.01, .1, 1., 10., 100., 300.):
            for name, ray in rays.items():
                bt = pm.apply_matrix(f.P3_TO_BT, ray)
                src = tuple(v * source_y / f.lum(bt) for v in bt)
                row = {'source_Y_nits': source_y, 'synthetic_P3_ray': name,
                       'source_BT2020': src}
                outputs = {}
                for label, fn in (('rgb_pre', old.chain), ('scalar_pre', chain)):
                    counters = collections.Counter()
                    try:
                        mapped = fn(src, meta, prepared, counters)
                        clipped, excursion = f.final_clip(mapped, meta['peak'])
                        outputs[label] = f.rgb_to_itp(tuple(f.pq_inverse(v) for v in clipped))
                        row[label] = {'final_Y_nits': f.lum(clipped),
                                      'physical_excursion': excursion, 'counters': dict(counters)}
                    except (ValueError, OverflowError, ZeroDivisionError) as exc:
                        row[label] = {'invalid': str(exc), 'counters': dict(counters)}
                if len(outputs) == 2:
                    row['delta720ITP_scalar_minus_rgb'] = [720 * (a-b) for a, b in
                        zip(outputs['scalar_pre'], outputs['rgb_pre'])]
                rows.append(row)
        report['shots'][shot] = {'metadata': meta,
            'metadata_sha256': hashlib.sha256(raw).hexdigest(), 'probes': rows}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(out)


if __name__ == '__main__':
    main()
