"""Focused source-only contracts for software IQ diagnostics (no panel claims)."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('iq_analyze', ROOT / 'tools/iq_analyze.py')
iq = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(iq)


def barcode(index, low=5., high=710., scale=1):
    """Independent reference raster; all captured bar rows are represented."""
    frame = np.full((20, 192), low)
    bits = [1, 0] + [(index >> n) & 1 for n in range(15, -1, -1)]
    bits += [((15 - index % 16) >> n) & 1 for n in range(3, -1, -1)] + [0, 1]
    for b, bit in enumerate(bits):
        frame[:8, b * 8:(b + 1) * 8] = high if bit else low
    for column in range(8):
        frame[16:, (4 * index + column) % 192] = high
    return np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        # The orchestration configures TMPDIR to its owned external scratch slot.
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('IQ_TEST_TMPDIR') or None)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_exact_packed_lengths_and_lazy_map(self):
        p = self.root / 'capture.raw'
        p.write_bytes(bytes(3 * 2 * 4 * 2))
        mapped = iq.map_xr30(p, 3, 2)
        self.assertIsInstance(mapped, np.memmap)
        self.assertEqual(mapped.shape, (2, 2, 3))
        with self.assertRaises(iq.AnalysisError):
            iq.map_xr30(p, 3, 2, single=True)
        p.write_bytes(bytes(25))
        with self.assertRaises(iq.AnalysisError):
            iq.map_xr30(p, 3, 2)

    def test_calibrated_endpoint_decode_and_identity_rejection(self):
        frame = barcode(37, scale=3)
        self.assertEqual(iq.decode_barcode(frame, 3, 192, 5, 710), (37, None))
        self.assertEqual(iq.decode_barcode(frame, 3, 192)[1], 'barcode_dead_band')
        with self.assertRaises(iq.AnalysisError):
            iq.decode_barcode(frame, 3, 192, 710, 5)

    def test_marker_checksum_and_torn_bar_rejected(self):
        frame = barcode(13)
        frame[:8, :8] = 5
        self.assertEqual(iq.decode_barcode(frame, 1, 192, 5, 710)[1], 'barcode_markers')
        frame = barcode(13)
        frame[:8, 18 * 8:19 * 8] = 710 - frame[:8, 18 * 8:19 * 8] + 5
        self.assertEqual(iq.decode_barcode(frame, 1, 192, 5, 710)[1], 'barcode_checksum')
        frame = barcode(13)
        frame[-1, 100:108] = 710
        self.assertEqual(iq.decode_barcode(frame, 1, 192, 5, 710)[1], 'bar_interior_blend_or_position_disagreement')

    def test_blends_and_wrapping_bar(self):
        a, b = barcode(47), barcode(48)
        for weight in (.3, .5, .7):
            self.assertEqual(iq.decode_barcode(weight * a + (1 - weight) * b, 1, 192, 5, 710)[1], 'barcode_dead_band')
        for index in (0, 46, 47, 48, 16383):
            self.assertEqual(iq.decode_barcode(barcode(index), 1, 192, 5, 710), (index, None))

    def test_timestamp_counts_monotonicity_and_missing_pts(self):
        p = self.root / 'capture.ts'
        p.write_text('0 100 8 110\n1 -1 9 120\n2 130 10 140\n')
        self.assertEqual(len(iq.parse_timestamps(p, 3)), 3)
        with self.assertRaises(iq.AnalysisError):
            iq.parse_timestamps(p, 2)
        p.write_text('0 100 8 110\n1 99 9 120\n')
        with self.assertRaises(iq.AnalysisError):
            iq.parse_timestamps(p, 2)
        p.write_text('0 100 8 110\n1 110 9 109\n')
        with self.assertRaises(iq.AnalysisError):
            iq.parse_timestamps(p, 2)
        p.write_text('0 100 8\n')
        with self.assertRaises(iq.AnalysisError):
            iq.parse_timestamps(p, 1)

    def test_intervals_never_bridge_rejection_or_sequence_gap(self):
        ts = [(n, n * 10, sequence, n * 10 + 1)
              for n, sequence in enumerate((1, 2, 3, 5, 6, 7))]
        report = iq.interval_report([0, None, 1, 2, 2, 3], ts)
        self.assertEqual(report['adjacent_valid_pairs'], 2)
        self.assertEqual(len(report['excluded_adjacent_pairs']), 3)
        self.assertEqual([v['sample_pair'] for v in report['observed_source_changes']], [[4, 5]])
        self.assertEqual(report['observed_source_changes'][0]['transition_bracket_upper_bound_ns'], 10)
        self.assertNotIn('hold_matches_ideal_fraction', report)

    def test_explicit_gap_limit_and_missing_pts_break_intervals(self):
        ts = [(0, 10, 1, 12), (1, 100, 2, 101), (2, -1, 3, 110)]
        report = iq.interval_report([0, 1, 2], ts, max_gap_ns=50)
        self.assertEqual(report['adjacent_valid_pairs'], 0)
        self.assertEqual(len(report['excluded_adjacent_pairs']), 2)
        self.assertEqual(report['timestamp_deltas_ns']['spa_pts'], [90, None])

    def test_plateaus_group_source_code_not_interpolated_columns(self):
        codes = np.repeat(np.arange(64, 97), 6)
        image = np.repeat(iq.pq(codes)[None, :, None], 3, axis=2)
        image = np.repeat(image, 8, axis=0)
        image += np.arange(len(codes))[None, :, None] * .001
        report = iq.plateau_report(image, codes, 1)
        self.assertEqual(report['source_code_plateau_count'], 33)
        self.assertEqual(len(report['plateaus']), 33)
        self.assertEqual(report['plateaus'][0]['source_columns'], [0, 5])
        self.assertGreater(report['plateaus'][0]['green_spatial_std_pq10'], 0)
        self.assertLess(abs(report['plateaus'][0]['green_residual_vs_identity_pq10']), .01)

    def test_manifest_schema_and_tampered_source(self):
        (self.root / 'manifest.json').write_text('{"schema":"unknown"}')
        with self.assertRaises(iq.AnalysisError):
            iq.validate_manifest(self.root)
        # Build a tiny genuine source fixture; generator's streaming path is shared
        # only for setup, then independently tamper source bytes and a design field.
        spec = importlib.util.spec_from_file_location('iq_test_gen', ROOT / 'scripts/generate_quality_stimuli.py')
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        dest = self.root / 'stimuli'
        gen.generate_stimuli(dest, 192, 72, [1], 1, 64 * 1024 * 1024)
        manifest, receipt = iq.validate_manifest(dest)
        self.assertTrue(receipt['all_source_hashes_verified'])
        selected = manifest['files'][0]['path']
        omitted = dest / manifest['files'][1]['path']
        omitted.unlink()
        _, partial = iq.validate_manifest(dest, [selected])
        self.assertEqual(partial['verified_source_paths'], [selected])
        self.assertFalse(partial['all_source_hashes_verified'])
        with self.assertRaises(iq.AnalysisError):
            iq.validate_manifest(dest)
        source = dest / selected
        with source.open('r+b') as stream:
            stream.seek(-1, 2)
            byte = stream.read(1)
            stream.seek(-1, 2)
            stream.write(bytes([byte[0] ^ 1]))
        with self.assertRaises(iq.AnalysisError):
            iq.validate_manifest(dest, [selected])
        manifest['files'][0]['expected'] = {}
        (dest / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(iq.AnalysisError):
            iq.validate_manifest(dest)

    def test_bar_interpolation_guard_and_independent_disagreement(self):
        scale, index = 4, 13
        frame = barcode(index, scale=scale)
        frame[16 * scale:17 * scale] = 350  # spatial interpolation at bar top
        # Linear transition only within the declared fixed source-pixel guard.
        for boundary, ascending in ((52, True), (60, False)):
            ramp = np.linspace(5, 710, 2 * scale, endpoint=False)
            frame[16 * scale:, boundary * scale - scale:boundary * scale + scale] = ramp if ascending else ramp[::-1]
        self.assertEqual(iq.decode_barcode(frame, scale, 192, 5, 710), (index, None))
        frame[-1, 100 * scale:108 * scale] = 710
        self.assertEqual(iq.decode_barcode(frame, scale, 192, 5, 710)[1], 'bar_interior_blend_or_position_disagreement')
        frame = barcode(index, scale=scale)
        frame[16 * scale:] = np.roll(frame[16 * scale:], 3 * scale, axis=1)
        self.assertEqual(iq.decode_barcode(frame, scale, 192, 5, 710)[1], 'bar_interior_blend_or_position_disagreement')

    def test_left_overlay_does_not_become_slanted_edge(self):
        args = iq.parser().parse_args(['run', 'stim', 'stim4k', '--width', '256', '--height', '160',
                                      '--scaling-scale', '1', '--scaling-y', '0'])
        edge = np.zeros((160, 256, 3))
        for y in range(160):
            boundary = 128 + .087488663526 * (y + .5 - 80)
            edge[y, :, :] = np.clip((np.arange(256) + .5 - boundary + 1) / 2, 0, 1)[:, None] * 710
        edge[:, :12] = 900  # desktop overlay at the left, far from fixed ROIs
        manifest = {'dimensions_and_timing': {'width': 256, 'height': 160},
                    'files': [{'path': 'scaling/scaling_p10.y4m', 'expected': {'slanted_edge': {'slope_dx_per_dy': .087488663526}}}]}
        report = iq.scaling_report(lambda name: edge if name.endswith('f2') else np.zeros_like(edge), manifest, args)
        self.assertEqual(report['slanted_edge_status'], 'diagnostic_only')
        self.assertLess(abs(report['placement_sanity']['edge_midpoint_median_output_px'] - 128), 1)
        self.assertLess(report['slanted_edge_10_90_width_out_px_median'], 4)

    def test_duplicate_scaling_scenes_reject_edge_measurement(self):
        args = iq.parser().parse_args(['run', 'stim', 'stim4k', '--width', '64', '--height', '64',
                                      '--scaling-scale', '1', '--scaling-y', '0'])
        image = np.zeros((64, 64, 3))
        image[:, 32:] = 710
        report = iq.scaling_report(lambda _: image, {'dimensions_and_timing': {'width': 64, 'height': 64},
                    'files': [{'path': 'scaling/scaling_p10.y4m', 'expected': {'slanted_edge': {'slope_dx_per_dy': 0.087488663526}}}]}, args)
        self.assertEqual(report['slanted_edge_status'], 'rejected_duplicate_grating_scene')
        self.assertIsNone(report['slanted_edge_10_90_width_out_px_median'])


if __name__ == '__main__':
    unittest.main()
