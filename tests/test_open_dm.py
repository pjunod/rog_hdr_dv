"""Deferred OPEN diagnostic regressions; never authored/vendor fixture fabrication.

Math-only control algebra is labelled separately. Positive source/result cases
require retained authentic frame256 and the once-rendered fixed variants supplied
by recovery after review. No test invokes an official tool or fits a curve.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import open_dm as dm
from tools.dolby_harness import open_dm_provenance as prov
from tools.dolby_harness import authored_master as am
from tools.dolby_harness.contracts import alignment, input_manifest, parse_json
from tools.dolby_harness.master_pixels import read_bounded


class OpenAlgebraTests(unittest.TestCase):
    def test_scalar_identity_and_direct_exponent(self):
        # Scalar serializer controls only, NOT XML/authored Dolby metadata.
        f = dm.factors('0,0,0,0,0,0,0,0,0')
        self.assertEqual(f['exact'], {'S': '1', 'O': '0', 'P': '1'})
        self.assertEqual(dm.factors('0,0,0,0,0,1,0,0,0')['exact']['P'], '2/3')

    def test_scalar_supported_range_and_gamma_clamp(self):
        for trim in ('0,0,0,2,0,0,0,0,0', '0,0,0,0,-2,0,0,0,0',
                     '0,0,0,nan,0,0,0,0,0', '0,0,0,0,0,inf,0,0,0'):
            with self.assertRaises(ValueError):
                dm.factors(trim)
        f = dm.factors('0,0,0,0,0,2,0,0,0')
        self.assertEqual(f['gamma_original'], '2')
        self.assertEqual(f['gamma_clamped'], '1')
        self.assertEqual(f['exact']['P'], '2/3')


class OpenProtocolMathTests(unittest.TestCase):
    # Synthetic mathematical protocol controls only; never source/authored/vendor
    # metadata. Missing pixels stop execution before any Vulkan/renderer call.
    def check_l1(self, anchors, accepted):
        native = Path(os.environ['HDR_OPEN_NATIVE'])
        volume = ['0', '1000', *map(str, am.P3)]
        values = ['DVH3', '1', '1', '1', *volume, *volume, *anchors, '1', '1', '0', '1']
        with tempfile.TemporaryDirectory(prefix='open-l1-math-') as tmp:
            root = Path(tmp)
            (root / 'control').write_text(' '.join(values) + '\n')
            proc = subprocess.run([str(native), str(root / 'control'), str(root / 'absent-input'),
                                   str(root / 'absent-output')], capture_output=True,
                                  env=prov.native_environment(root), timeout=30)
            self.assertEqual(proc.returncode, 1 if accepted else 2)
            self.assertIn(b'No successful OPEN' if accepted else b'Invalid DVH3', proc.stderr)
            self.assertNotIn(b'Explicit OPEN metadata rejected', proc.stderr)
            self.assertEqual(proc.stdout, b'')
            self.assertFalse((root / 'absent-output').exists())

    def test_equal_decimal_flat_and_collapsed_l1_acceptance(self):
        for anchors in (('0.1', '0.1', '0.8'), ('0.1', '0.1', '0.1'),
                        ('0', '0.1', '0.1')):
            with self.subTest(anchors=anchors):
                self.check_l1(anchors, accepted=True)

    def test_descending_and_invalid_l1_rejection(self):
        for anchors in (('0.100000001', '0.1', '0.8'),
                        ('0', '0.100000001', '0.1'), ('0.1', '0', '0.8'),
                        ('0', '0.8', '0.1'), ('nan', '0.1', '0.8'),
                        ('0', 'inf', '1'), ('0', '0.1', '1.000000001'),
                        ('-0.000000001', '0.1', '1')):
            with self.subTest(anchors=anchors):
                self.check_l1(anchors, accepted=False)


class OpenAuthenticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = Path(os.environ['HDR_AUTHORED_INPUT'])
        cls.obj, _, cls.meta = input_manifest(cls.manifest)
        if cls.obj['frame']['index'] != 256:
            raise AssertionError('retained authentic256 required; no substitute')
        cls.native = Path(os.environ['HDR_OPEN_NATIVE'])
        cls.compile = parse_json(read_bounded(os.environ['HDR_OPEN_COMPILE'], 4 * 1024 * 1024))

    def test_real_selection_factors_and_unapplied_fields(self):
        a = dm.algorithm(self.obj, self.meta, 'l1-hermite-sop')
        self.assertEqual(a['derived_factors']['exact'], {'S': '507/500', 'O': '-7/500', 'P': '2000/2001'})
        self.assertEqual(a['original_trim'], '0,0,0,-0.028,0,0.001,-0.002,0,-0.75')
        self.assertEqual(a['unapplied_trim_values']['6'], '-0.002')
        self.assertEqual(a['unapplied_trim_values']['8'], '-0.75')
        self.assertIsNone(a['selected_cm_name'])
        self.assertFalse(a['full_mapping_complete'])
        self.assertEqual(a['source_records'], self.meta['records'])
        self.assertEqual(a['l1'], {'min_pq': 0.0, 'avg_pq': 0.290273, 'max_pq': 0.879591})
        saved = copy.deepcopy(self.meta)
        for variant in dm.VARIANTS:
            with self.subTest(variant=variant):
                a = dm.algorithm(self.obj, self.meta, variant)
                indexes = ([0, 1, 2, 8] if variant == dm.RGB_VARIANT else
                           [0, 1, 2, 6, 7, 8] if variant in dm.SOP_VARIANTS else list(range(9)))
                self.assertEqual(a['unapplied_trim_indexes'], indexes)
                self.assertEqual(a['unapplied_trim_values'],
                                 {str(i): a['original_trim'].split(',')[i] for i in indexes})
                self.assertEqual(a['derived_factors']['exact'],
                                 {'S': '507/500', 'O': '-7/500', 'P': '2000/2001'})
                self.assertEqual(a['applied_factors'], a['derived_factors']['float']
                                 if variant in dm.SOP_VARIANTS else {'S': 1.0, 'O': 0.0, 'P': 1.0})
        self.assertEqual(self.meta, saved)

    def test_fixed_variant_control_geometry_domain(self):
        saved = copy.deepcopy(self.meta)
        for i, variant in enumerate(dm.VARIANTS):
            tokens = dm.control(self.obj, self.meta, variant).split()
            self.assertEqual(tokens[:4], ['DVH3', '4096', '2160', '1'])
            self.assertEqual(len(tokens), 33 if variant == dm.RGB_VARIANT else 31)
            self.assertEqual(int(tokens[27]), i)
            self.assertEqual(tokens[24:27], ['0.0', '0.290273', '0.879591'])
            if i < 2:
                self.assertEqual(tokens[28:], ['1.0', '0.0', '1.0'])
        self.assertEqual(saved, self.meta)
        self.assertEqual(dm.algorithm(self.obj, self.meta, 'l1-rational')['l1_curve_domain'], 'nits rational')

    def test_duplicate_selection_and_conflict_rejection(self):
        m = copy.deepcopy(self.meta)
        selected = next(r for r in m['records'] if r['level'] == 2 and r['target_id'] == 27)
        duplicate = copy.deepcopy(selected)
        duplicate['scope'] = 'frame'
        m['records'].append(duplicate)
        self.assertEqual(dm.algorithm(self.obj, m, 'l1-hermite-sop')['derived_factors'],
                         dm.algorithm(self.obj, self.meta, 'l1-hermite-sop')['derived_factors'])
        next(f for f in duplicate['fields'] if f['name'] == 'Trim')['text'] = '0,0,0,0,0,0,0,0,0'
        # Rejection-only mutation of verified real record; never vendor input.
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            dm.algorithm(self.obj, m, 'l1-hermite-sop')

    def test_exact_target_and_variant_no_nearest_fallback(self):
        for field, value in (('id', '28'), ('max_nits', 601), ('min_nits', 0.001)):
            obj = copy.deepcopy(self.obj)
            obj['target'][field] = value
            with self.assertRaises(ValueError):
                dm.algorithm(obj, self.meta, 'l1-hermite-sop')
        with self.assertRaises(ValueError):
            dm.algorithm(self.obj, self.meta, 'stock')

    def test_native_protocol_rejection_before_vulkan(self):
        tokens = dm.control(self.obj, self.meta, 'l1-hermite-sop').split()
        wrong = [tokens + ['trailing'], tokens[:-1], ['DVH2'] + tokens[1:]]
        for index, value in ((1, '4097'), (3, '0'), (24, 'nan'), (25, '-1'),
                             (26, '0'), (27, '4'), (28, '2'), (30, '0')):
            t = tokens[:]
            t[index] = value
            wrong.append(t)
        with tempfile.TemporaryDirectory(prefix='open-protocol-') as tmp:
            root = Path(tmp)
            for values in wrong:
                (root / 'control').write_text(' '.join(values) + '\n')
                proc = subprocess.run([str(self.native), str(root / 'control'), str(root / 'absent-input'),
                                       str(root / 'absent-output')], capture_output=True,
                                      env=prov.native_environment(root), timeout=30)
                self.assertEqual(proc.returncode, 2)
                self.assertIn(b'Invalid DVH3', proc.stderr)
                self.assertFalse((root / 'absent-output').exists())

    def test_actual_compile_source_header_library_abi_closure(self):
        prov.validate_compile(self.compile, live=True)
        self.assertEqual(self.compile['abi'], 365)
        self.assertEqual(self.compile['binary_sha256'], prov.sha(self.native))
        for edit in ('abi', 'sources', 'library_sources', 'headers'):
            c = copy.deepcopy(self.compile)
            if edit == 'abi':
                c['abi'] = 361
            elif edit in ('sources', 'library_sources'):
                key = next(iter(c[edit]))
                c[edit][key] = '0' * 64
            else:
                c['headers'] = {}
            with self.assertRaises(ValueError):
                prov.validate_compile(c)


class OpenActualResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only the new once-rendered RGB variant belongs to this source. The
        # original303/315 results retain OLD frontend/ABI362/364 identities.
        cls.paths = parse_json(read_bounded(os.environ['HDR_OPEN_RESULTS'], 4 * 1024 * 1024))
        if set(cls.paths) != {dm.RGB_VARIANT}:
            raise AssertionError('new RGB result required; no old-result relabelling')

    def test_genuine_source_bound_results_and_rejection_only_tampering(self):
        for variant in self.paths:
            path = Path(self.paths[variant])
            r, pixels = dm.validate_result(path)
            self.assertEqual(r['algorithm']['variant'], variant)
            self.assertEqual(len(pixels), 4096 * 2160)
            del pixels
            self.assertEqual(r['source_alignment']['frame_index'], 256)
            self.assertEqual(r['algorithm']['applied_factors']['S'], 1.014)
            for field in ('algorithm', 'encoding', 'source_alignment', 'provenance'):
                changed = copy.deepcopy(r)
                if field == 'algorithm':
                    changed[field]['applied_factors']['P'] = 1.1
                elif field == 'encoding':
                    changed[field]['transfer'] = 'linear'
                elif field == 'source_alignment':
                    changed[field]['frame_index'] = 0
                else:
                    changed[field]['execution']['native_sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    dm.validate_result(path, json.dumps(changed).encode())


if __name__ == '__main__':
    unittest.main()
