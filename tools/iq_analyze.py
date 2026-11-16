#!/usr/bin/env python3
"""Offline software-capture diagnostics; no optical or panel-cadence acceptance.

Derived from Claude's inherited November 15, 2026 iq_analyze.py implementation.
Reworked for validation, portable geometry and bounded per-frame analysis.
Only NumPy and the Python standard library are required.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np


class AnalysisError(ValueError):
    """An input cannot support the requested diagnostic."""


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_manifest(root, required_paths=None):
    """Verify complete design metadata and byte hashes for the selected sources."""
    root = Path(root).resolve()
    manifest_path = root / 'manifest.json'
    m = json.loads(manifest_path.read_text())
    if m.get('schema') != 'image-quality-stimuli-v1':
        raise AnalysisError('unsupported stimulus manifest schema')
    source = Path(__file__).resolve().parents[1] / 'scripts/generate_quality_stimuli.py'
    spec = importlib.util.spec_from_file_location('_iq_stimuli', source)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    try:
        timing = m['dimensions_and_timing']
        params = {k: timing[k] for k in ('width', 'height', 'cadence_fps', 'cadence_seconds')}
        gen.validate_parameters(params['width'], params['height'], params['cadence_fps'],
                                params['cadence_seconds'], 2**63 - 1)
        records = gen.plan(params['width'], params['height'], params['cadence_fps'], params['cadence_seconds'])
        design = [{k: r[k] for k in ('path', 'header', 'frames', 'size', 'stimulus', 'format', 'expected')}
                  for r in records]
        for item in design:
            item['header'] = item['header'].decode('ascii')
        expected_hashes = {'generator_sha256': digest_file(source),
                           'parameters_canonical_json_sha256': gen.sha256(gen.canonical_json(params)),
                           'design_canonical_json_sha256': gen.sha256(gen.canonical_json(design))}
        if m['input_hashes'] != expected_hashes:
            raise AnalysisError('manifest generator/parameter/design hash mismatch')
        if len(m['files']) != len(records):
            raise AnalysisError('manifest file count differs from pinned design')
        if timing['stimulus_bytes_total'] != sum(r['size'] for r in records):
            raise AnalysisError('manifest total byte count mismatch')
        requested = None if required_paths is None else set(required_paths)
        available = {f['path'] for f in m['files']}
        if requested is not None and not requested <= available:
            raise AnalysisError('required stimulus path absent from manifest')
        verified_paths = []
        for f, r in zip(m['files'], records):
            for key, record_key in [('path', 'path'), ('bytes', 'size'), ('stimulus', 'stimulus'),
                                    ('format', 'format'), ('frame_count', 'frames'), ('expected', 'expected')]:
                if f[key] != r[record_key]:
                    raise AnalysisError('manifest design field mismatch: ' + key)
            if requested is not None and f['path'] not in requested:
                continue
            path = (root / f['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise AnalysisError('stimulus path escapes root or is missing')
            if path.stat().st_size != f['bytes'] or digest_file(path) != f['sha256']:
                raise AnalysisError('stimulus size/hash mismatch: ' + f['path'])
            verified_paths.append(f['path'])
    except (KeyError, TypeError, gen.StimulusError) as exc:
        raise AnalysisError('malformed stimulus manifest: ' + str(exc)) from exc
    return m, {'manifest_sha256': digest_file(manifest_path),
               'verified_source_paths': verified_paths,
               'all_source_hashes_verified': len(verified_paths) == len(m['files'])}


def map_xr30(path, width, height, single=False):
    """Memory-map packed little-endian XR30; never materialize a complete movie."""
    path = Path(path)
    if width <= 0 or height <= 0:
        raise AnalysisError('capture dimensions must be positive')
    size = path.stat().st_size
    frame_bytes = width * height * 4
    if not size or size % frame_bytes or (single and size != frame_bytes):
        raise AnalysisError('XR30 byte length does not match geometry: ' + str(path))
    return np.memmap(path, dtype='<u4', mode='r', shape=(size // frame_bytes, height, width))


def rgb(packed):
    return np.stack([(packed >> 20) & 1023, (packed >> 10) & 1023, packed & 1023], axis=-1).astype(float)


def pq(code):
    return (np.asarray(code) - 64) * 1023 / 876


def plateau_report(image, codes, scale):
    """Aggregate interiors by source CODE, not by interpolated output columns."""
    codes = np.asarray(codes)
    if image.shape[1] != len(codes) * scale:
        raise AnalysisError('dither width does not match column manifest')
    if len(np.unique(codes)) != 33 or np.any(np.diff(codes) < 0):
        raise AnalysisError('dither manifest must contain 33 ordered source codes')
    plateaus = []
    for code in np.unique(codes):
        columns = np.flatnonzero(codes == code)
        # Exclude each plateau's boundary source pixel to reduce scaler-edge mixing.
        start, end = (int(columns[0]) + 1) * scale, int(columns[-1]) * scale
        if end <= start:
            raise AnalysisError('source plateau too narrow for interior sampling')
        samples = image[:, start:end]
        means = samples.mean(axis=(0, 1))
        plateaus.append({'source_code': int(code), 'source_columns': [int(columns[0]), int(columns[-1])],
                         'rgb_mean_pq10': means.tolist(),
                         'identity_pq10': float(pq(code)),
                         'green_residual_vs_identity_pq10': float(means[1] - pq(code)),
                         'green_spatial_std_pq10': float(samples[..., 1].std()),
                         'green_spatial_min_max_pq10': [float(samples[..., 1].min()), float(samples[..., 1].max())],
                         'mean_channel_spread_pq10': float(np.ptp(means))})
    return {'source_code_plateau_count': len(plateaus), 'plateaus': plateaus,
            'limitation': 'Spatial texture and identity-PQ residuals only; no bit-depth, dither or optical acceptance inferred.'}


def crossing(profile, endpoints, start=0, stop=None, fraction=0.5):
    low, high = endpoints
    if abs(high - low) < 1e-9:
        return None
    target = low + fraction * (high - low)
    for i in range(max(0, start), min(len(profile) - 1, stop if stop is not None else len(profile) - 1)):
        p, q = profile[i] - target, profile[i + 1] - target
        if p == 0:
            return i + 0.5
        if p * q < 0:
            return i + 0.5 + p / (p - q)
    return None


def decode_barcode(frame, scale, source_width, low=0., high=1023.):
    """Decode observed green using externally supplied endpoint calibration.

    All captured bar interior rows (source y>=17) must agree with the index.
    One fixed source-pixel strip at the y=16 top boundary is excluded for scaling. This
    rejects a tear even if only one of those rows disagrees. Crops shorter than
    the source frame cannot exclude tears outside the crop.
    """
    if not (math.isfinite(low) and math.isfinite(high) and 0 <= low < high <= 1023):
        raise AnalysisError('barcode endpoints require 0 <= low < high <= 1023')
    if scale < 1 or frame.shape[1] != source_width * scale or frame.shape[0] < 18 * scale:
        raise AnalysisError('cadence crop geometry cannot contain barcode and bar')
    mid, dead = (high + low) / 2, (high - low) / 4
    margin = max(1, scale)
    means = np.array([frame[scale:7 * scale, b * 8 * scale + margin:(b + 1) * 8 * scale - margin].mean()
                      for b in range(24)])
    if np.any(np.abs(means - mid) < dead):
        return None, 'barcode_dead_band'
    bits = (means > mid).astype(int).tolist()
    if bits[:2] != [1, 0] or bits[-2:] != [0, 1]:
        return None, 'barcode_markers'
    index = sum(bit << (15 - n) for n, bit in enumerate(bits[2:18]))
    check = sum(bit << (3 - n) for n, bit in enumerate(bits[18:22]))
    if check != 15 - index % 16:
        return None, 'barcode_checksum'
    expected = np.zeros(source_width, bool)
    expected[(np.arange(8) + 4 * index) % source_width] = True
    # A fixed one-source-pixel guard on both sides of the two known bar
    # boundaries permits scaler interpolation there. Everything else, on every
    # captured interior bar row, must be stable and agree with the decoded index.
    # The same fixed guard excludes source y=[16,17) at the bar top boundary.
    expected_pixels = np.repeat(expected, scale)
    centres = np.arange(source_width * scale) + .5
    stable = np.ones(len(centres), dtype=bool)
    for boundary in ((4 * index) % source_width, (4 * index + 8) % source_width):
        distance = np.abs(centres - boundary * scale)
        distance = np.minimum(distance, source_width * scale - distance)
        stable &= distance >= scale
    bar = frame[17 * scale:, stable]
    if np.any(np.abs(bar - mid) < dead) or np.any((bar > mid) != expected_pixels[stable][None, :]):
        return None, 'bar_interior_blend_or_position_disagreement'
    return index, None


def parse_timestamps(path, frames):
    """Four integer fields: capture ordinal, SPA PTS ns, SPA sequence, receive ns."""
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        try:
            values = tuple(map(int, line.split()))
        except ValueError as exc:
            raise AnalysisError('timestamp row contains non-integer fields') from exc
        if len(values) != 4:
            raise AnalysisError('timestamp rows require ordinal, PTS, sequence, receive_ns')
        rows.append(values)
    if len(rows) != frames:
        raise AnalysisError('timestamp row/frame count mismatch')
    for n, row in enumerate(rows):
        if row[0] != n or row[3] < 0 or row[1] < -1 or row[2] < -1:
            raise AnalysisError('invalid timestamp ordinal or negative timestamp/sequence')
        if n and row[3] <= rows[n - 1][3]:
            raise AnalysisError('receive timestamps must be strictly increasing')
    pts = [r[1] for r in rows if r[1] >= 0]
    if any(b <= a for a, b in zip(pts, pts[1:])):
        raise AnalysisError('available SPA PTS must be strictly increasing')
    return rows


def interval_report(indices, timestamps, max_gap_ns=None):
    """Adjacent samples only; never bridge rejected images or timestamp records."""
    if len(indices) != len(timestamps):
        raise AnalysisError('decoded/timestamp count mismatch')
    changes, gaps, valid_pairs = [], [], 0
    for n in range(1, len(indices)):
        a, b = timestamps[n - 1], timestamps[n]
        receive_delta = b[3] - a[3]
        pts_delta = b[1] - a[1] if a[1] >= 0 and b[1] >= 0 else None
        reasons = []
        if indices[n - 1] is None or indices[n] is None:
            reasons.append('rejected_sample')
        if a[2] < 0 or b[2] < 0:
            reasons.append('sequence_unavailable')
        elif b[2] != a[2] + 1:
            reasons.append('sequence_gap_or_reset')
        if pts_delta is None:
            reasons.append('pts_unavailable')
        if max_gap_ns is not None and (receive_delta > max_gap_ns or (pts_delta is not None and pts_delta > max_gap_ns)):
            reasons.append('explicit_timestamp_gap_limit')
        pair = {'sample_pair': [n - 1, n], 'spa_pts_delta_ns': pts_delta, 'receive_delta_ns': receive_delta}
        if reasons:
            gaps.append(dict(pair, reasons=reasons))
            continue
        valid_pairs += 1
        if indices[n] != indices[n - 1]:
            changes.append(dict(pair, source_indices=[indices[n - 1], indices[n]],
                                source_index_step=indices[n] - indices[n - 1],
                                transition_bracket_upper_bound_ns=pts_delta))
    return {'quality': 'diagnostic_only', 'adjacent_valid_pairs': valid_pairs,
            'excluded_adjacent_pairs': gaps, 'observed_source_changes': changes,
            'timestamp_deltas_ns': {'spa_pts': [b[1] - a[1] if a[1] >= 0 and b[1] >= 0 else None
                                               for a, b in zip(timestamps, timestamps[1:])],
                                    'receive': [b[3] - a[3] for a, b in zip(timestamps, timestamps[1:])]},
            'gap_limit_ns': max_gap_ns,
            'limitation': 'SPA PTS is software stream timing, receive time is callback timing. Neither measures panel refresh. '
                          'Each transition is bracketed by adjacent valid samples; rejected samples and sequence gaps break intervals. '
                          'Without an explicit gap limit, time gaps are listed but cannot be classified as dropped records.'}


def file_entry(manifest, path):
    matches = [f for f in manifest['files'] if f['path'] == path]
    if len(matches) != 1:
        raise AnalysisError('missing or duplicate manifest entry: ' + path)
    return matches[0]


def analyze(args):
    man, verified = validate_manifest(args.stim)
    man4, verified4 = validate_manifest(args.stim4k, ['scaling/scaling_p10.y4m'])
    sw, sh = (man['dimensions_and_timing'][k] for k in ('width', 'height'))
    scale = args.stim_scale
    x, y = args.stim_x, args.stim_y
    width, height = sw * scale, sh * scale
    if min(x, y) < 0 or x + width > args.width or y + height > args.height:
        raise AnalysisError('stimulus placement exceeds capture frame')
    def still(name):
        return rgb(map_xr30(args.run / (name + '.xr30'), args.width, args.height, single=True)[0])
    out = {'schema': 'iq-software-analysis-v1', 'status': 'diagnostic_only_no_universal_iq_threshold',
           'scope': 'Compositor XR30 RGB code diagnostics; no optical accuracy, Dolby Vision or physical panel cadence claim.',
           'source_verification': {'stim': verified, 'stim4k': verified4},
           'geometry': {'capture': [args.width, args.height], 'stim_rect': [x, y, width, height], 'stim_scale': scale}}
    d = file_entry(man, 'dither/dither_ramps_p10.y4m')['expected']
    out['range_and_dither'] = {}
    for n, name in enumerate(('near_black', 'mid_grey')):
        ramp = d['ramps'][n] if 'ramps' in d else d[name]
        image = still('dither-f' + str(n))[y + height // 4:y + 3 * height // 4, x:x + width]
        out['range_and_dither'][name] = plateau_report(image, ramp['column_codes'], scale)
    sit = {}
    for tag in ('c420mpeg2', 'c420jpeg', 'c420paldv'):
        e = file_entry(man, f'chroma_siting/chroma_siting_{tag}_8bit.y4m')['expected']
        sit[tag] = {'tag_implied': e['siting_tag_implied']}
        for n, key, axis in ((0, 'vertical_edges', 'x'), (1, 'horizontal_edges', 'y')):
            image = still(f'siting-{tag}-f{n}')[y:y + height, x:x + width, 0]
            profile = (image[height // 3:2 * height // 3].mean(axis=0) if axis == 'x'
                       else image[:, width // 3:2 * width // 3].mean(axis=1))
            observed = []
            for edge in e[key]:
                expected = edge[f'midpoint_luma_{axis}_for_this_file']
                start, end = max(0, int((expected - 4) * scale)), min(len(profile), int((expected + 4) * scale))
                segment = profile[start:end]
                endpoints = (float(segment[:scale].mean()), float(segment[-scale:].mean()))
                c = crossing(profile, endpoints, start, end - 1)
                observed.append({'tag_source_domain_midpoint': expected,
                                 'observed_rgb_midpoint_source_px': None if c is None else c / scale,
                                 'observed_rgb_endpoints_pq10': endpoints})
            sit[tag][key] = observed
    pairs = {}
    for tag, key in (('c420jpeg', 'vertical_edges'), ('c420paldv', 'horizontal_edges')):
        pairs[tag + '_minus_c420mpeg2_' + key] = [None if a['observed_rgb_midpoint_source_px'] is None or b['observed_rgb_midpoint_source_px'] is None
                                               else a['observed_rgb_midpoint_source_px'] - b['observed_rgb_midpoint_source_px']
                                               for a, b in zip(sit[tag][key], sit['c420mpeg2'][key])]
    out['chroma_siting'] = {'observed': sit, 'tag_pair_relative_shifts_source_px': pairs,
                            'limitation': 'RGB midpoints after tone/gamut mapping are not source-code chroma midpoints; no source-domain siting correctness inferred.'}
    out['scaling'] = scaling_report(still, man4, args)
    cadence = {}
    crop_width = sw * scale
    for fps in man['dimensions_and_timing']['cadence_fps']:
        raw = args.run / f'cadence-{fps}.raw'
        if not raw.exists():
            cadence[str(fps)] = {'status': 'not_captured'}
            continue
        movie = map_xr30(raw, crop_width, args.cadence_height)
        ts = parse_timestamps(args.run / f'cadence-{fps}.ts', len(movie))
        indices, rejects = [], Counter()
        count_source = file_entry(man, f'cadence/cadence_{fps}fps_p10.y4m')['frame_count']
        for packed in movie:
            green = ((packed >> 10) & 1023).astype(float)
            index, reason = decode_barcode(green, scale, sw, args.barcode_low, args.barcode_high)
            if index is not None and index >= count_source:
                index, reason = None, 'index_outside_source'
            indices.append(index)
            if reason:
                rejects[reason] += 1
        report = interval_report(indices, ts, args.max_timestamp_gap_ns)
        report.update(captured_frames=len(movie), decoded_frames=sum(i is not None for i in indices),
                      rejection_counts=dict(rejects), decoded_indices=indices,
                      calibration_status='explicit_measured_endpoints' if args.calibrated else 'identity_default_unvalidated',
                      barcode_endpoints=[args.barcode_low, args.barcode_high],
                      status='diagnostic_only' if args.calibrated else 'rejected_for_cadence_inference_uncalibrated_identity_thresholds',
                      bar_rows_checked=[17 * scale, args.cadence_height],
                      bar_excluded_top_transition_source_rows=[16, 17],
                      bar_boundary_guard_source_px=1,
                      bar_scope='Every captured interior bar row checked after the fixed top transition strip [16,17) source rows, '
                                'outside fixed one-source-pixel guards around expected left/right boundaries. '
                                'Tears inside boundary guards or outside the crop cannot be excluded.')
        cadence[str(fps)] = report
    out['software_cadence'] = cadence
    return out


def scaling_report(still, manifest, args):
    source_w, source_h = (manifest['dimensions_and_timing'][k] for k in ('width', 'height'))
    s = args.scaling_scale
    if not math.isfinite(s) or s <= 0:
        raise AnalysisError('scaling scale must be finite and positive')
    w, h = round(source_w * s), round(source_h * s)
    x, y = args.scaling_x, args.scaling_y
    if s <= 0 or not math.isfinite(s) or min(x, y) < 0 or x + w > args.width or y + h > args.height or min(w, h) < 32:
        raise AnalysisError('invalid scaling placement/geometry')
    edge = still('scaling4k-f2')[y:y + h, x:x + w, 1]
    # Predetermined interior endpoint ROIs avoid desktop overlays at the edges.
    endpoint_rois = [(w // 4, w // 3), (2 * w // 3, 3 * w // 4)]
    patches = [edge[h // 4:3 * h // 4, left:right] for left, right in endpoint_rois]
    low, high = [float(patch.mean()) for patch in patches]
    spread = [float(patch.std()) for patch in patches]
    sane = high > low and high - low > 4 * max(spread + [0.25])
    widths, positions = [], []
    slope = file_entry(manifest, 'scaling/scaling_p10.y4m')['expected']['slanted_edge']['slope_dx_per_dy']
    # Fixed search radius is 4 source pixels, chosen before observing the image.
    search_radius = max(2, math.ceil(4 * s))
    rejected_rows = 0
    for row_index in range(h // 4, 3 * h // 4):
        row = edge[row_index]
        predicted = w / 2 + slope * (row_index + .5 - h / 2)
        start, stop = math.floor(predicted - search_radius), math.ceil(predicted + search_radius)
        if start < w // 3 or stop >= 2 * w // 3:
            rejected_rows += 1
            continue
        p10, p90 = (crossing(row, (low, high), start, stop, fraction=f) for f in (.1, .9))
        pmid = crossing(row, (low, high), start, stop)
        if p10 is None or p90 is None or pmid is None or not p10 < pmid < p90:
            rejected_rows += 1
            continue
        widths.append(p90 - p10)
        positions.append(pmid)
    if rejected_rows:
        sane = False
    gr = still('scaling4k-f1')[y:y + h, x:x + w, 1]
    duplicate_scene = bool(np.array_equal(gr, edge))
    if duplicate_scene:
        sane = False
    modulation = {}
    for name, yi, xi, axis in [('vertical_1px', 0, 0, 0), ('vertical_2px', 0, 1, 0),
                                ('horizontal_1px', 1, 0, 1), ('horizontal_2px', 1, 1, 1)]:
        q = gr[int((yi / 2 + .08) * h):int((yi / 2 + .42) * h),
               int((xi / 2 + .08) * w):int((xi / 2 + .42) * w)]
        profile = q.mean(axis=axis)
        modulation[name] = float((np.percentile(profile, 95) - np.percentile(profile, 5)) / (high - low)) if sane else None
    zone = still('scaling4k-f0')[y:y + h, x:x + w, 1]
    row = zone[max(0, h // 2 - 1):h // 2 + 1].mean(axis=0)
    radius = math.hypot(source_w, source_h)
    scan = []
    for centre in range(32, w - 32, 64):
        segment = row[centre - 32:centre + 32]
        win = np.hanning(len(segment))
        spectrum = abs(np.fft.rfft((segment - segment.mean()) * win))
        k = int(np.argmax(spectrum[1:])) + 1
        scan.append({'dx_out': centre - w / 2, 'amplitude_pq10': float(2 * spectrum[k] / win.sum()),
                     'dominant_cycles_per_output_px': k / len(segment),
                     'source_local_cycles_per_output_px': abs(centre - w / 2) / (radius * s * s)})
    return {'scale': s, 'configured_rect': [x, y, w, h], 'observed_endpoints_pq10': [low, high],
            'endpoint_spatial_std_pq10': spread,
            'endpoint_rois_output_px': [[left, h // 4, right - left, h // 2] for left, right in endpoint_rois], 'endpoint_sanity': 'usable' if sane else 'rejected',
            'placement_sanity': {'edge_rows_with_midpoint': len(positions),
                                 'edge_midpoint_median_output_px': float(np.median(positions)) if positions else None,
                                 'configured_centre_output_px': w / 2,
                                 'search_radius_source_px': 4, 'rejected_edge_rows': rejected_rows,
                                 'limitation': 'Configured rectangle and central edge are sanity diagnostics, not independent placement registration.'},
            'grating_modulation_relative_to_observed_endpoints': modulation,
            'slanted_edge_status': ('rejected_duplicate_grating_scene' if duplicate_scene else
                                    'diagnostic_only' if sane and widths and np.median(widths) > 0 else 'rejected_missing_or_invalid_edge'),
            'slanted_edge_10_90_width_out_px_median': float(np.median(widths)) if widths and sane and np.median(widths) > 0 else None,
            'alias_boundary_abs_dx_out': .5 * radius * s * s, 'zone_plate_scan': scan,
            'limitation': 'Observed slanted-edge endpoints normalize modulation because PQ source white is 10000 nits and may tone map. '
                          'Tone/gamut mapping, capture placement and scaler phase confound these diagnostics; no quality acceptance threshold established.'}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'stim', 'stim4k'):
        p.add_argument(name, type=Path)
    for name, default in [('width', 2560), ('height', 1600), ('stim-x', 512), ('stim-y', 368),
                          ('stim-scale', 8), ('scaling-x', 0), ('scaling-y', 80), ('cadence-height', 160)]:
        p.add_argument('--' + name, type=int, default=default)
    p.add_argument('--scaling-scale', type=float, default=2 / 3)
    p.add_argument('--barcode-low', type=float, help='independently measured low green PQ10 endpoint')
    p.add_argument('--barcode-high', type=float, help='independently measured high green PQ10 endpoint')
    p.add_argument('--max-timestamp-gap-ns', type=int, help='explicit maximum adjacent timestamp delta; never inferred from content')
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    args.calibrated = args.barcode_low is not None and args.barcode_high is not None
    if (args.barcode_low is None) != (args.barcode_high is None):
        p.error('provide both measured barcode endpoints')
    if not args.calibrated:
        args.barcode_low, args.barcode_high = 0., 1023.
    if not 0 <= args.barcode_low < args.barcode_high <= 1023:
        p.error('barcode endpoints require 0 <= low < high <= 1023')
    if args.stim_scale < 1 or (args.max_timestamp_gap_ns is not None and args.max_timestamp_gap_ns <= 0):
        p.error('scale and optional timestamp gap limit must be positive')
    try:
        out = analyze(args)
        destination = args.run / 'analysis.json'
        with destination.open('x') as stream:
            json.dump(out, stream, indent=2, allow_nan=False)
            stream.write('\n')
    except (AnalysisError, OSError, ValueError, KeyError) as exc:
        print('iq_analyze: ' + str(exc), file=sys.stderr)
        return 1
    print(str(destination))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
