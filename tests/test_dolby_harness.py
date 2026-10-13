"""Deferred stage-1 regression batch. Native tests require HDR_HARNESS_NATIVE.

No Dolby metadata is generated, not even an identity RPU. Metadata validation
cases exercise missing/mismatched/rejected inputs before any reshaping data.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness.contracts import ENCODING, alignment, input_manifest, load_json, result_manifest
from tools.dolby_harness.harness import compare, render
from tools.dolby_harness.metric import compare_pixels, delta_itp, pq_eotf, pq_inverse, rgb_to_itp, summarize

BT2020 = [0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290]


class MetricTests(unittest.TestCase):
    def test_pq_endpoints_and_roundtrip(self):
        self.assertEqual(pq_eotf(0), 0)
        self.assertAlmostEqual(pq_eotf(1), 10000, places=5)
        for nits in (0.0004, 0.1, 1, 100, 203, 616, 1000, 10000):
            self.assertAlmostEqual(pq_eotf(pq_inverse(nits)), nits, delta=max(nits * 1e-9, 1e-9))

    def test_achromatic_and_known_delta(self):
        i, t, p = rgb_to_itp((0.5, 0.5, 0.5))
        self.assertAlmostEqual(i, 0.5, places=12)
        self.assertAlmostEqual(t, 0, places=12)
        self.assertAlmostEqual(p, 0, places=12)
        self.assertAlmostEqual(compare_pixels([(0.5,) * 3], [(0.501,) * 3])['mean'], 0.72, places=9)

    def test_annex4_public_vector(self):
        itp = rgb_to_itp((296 / 1023, 201 / 1023, 582 / 1023))
        for got, expected in zip(itp, (0.3554, 0.1346, -0.1613)):
            self.assertAlmostEqual(got, expected, delta=0.0001)

    def test_itp_weighting(self):
        self.assertEqual(delta_itp((0, 0, 0), (0, 0.5, 0)), 360)
        self.assertEqual(delta_itp((0, 0, 0), (0, 0, 1)), 720)

    def test_summary_nearest_rank(self):
        r = summarize(range(1, 21))
        self.assertEqual(r['pixels'], 20)
        self.assertEqual(r['mean'], 10.5)
        self.assertEqual(r['p95'], 19)
        self.assertEqual(r['max'], 20)
        self.assertEqual(summarize([2])['p95'], 2)

    def test_invalid_metric_inputs(self):
        for value in (-0.001, 1.001, math.nan, math.inf):
            with self.assertRaises(ValueError):
                pq_eotf(value)
        for values in ([], [math.nan], [-1]):
            with self.assertRaises(ValueError):
                summarize(values)
        with self.assertRaises(ValueError):
            compare_pixels([(0, 0, 0)], [])


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        raw = struct.pack('<12f', 0, 0, 0, 0.2, 0.1, 0.05, 0.5, 0.5, 0.5, 0.65, 0.4, 0.2)
        (self.root / 'input.f32').write_bytes(raw)
        self.obj = {'schema': 1,
                    'frame': {'input': {'file': 'input.f32', 'sha256': hashlib.sha256(raw).hexdigest()},
                              'width': 2, 'height': 2, 'index': 1, 'pts': {'num': 1, 'den': 24},
                              'content_id': 'public-synthetic-asymmetric-pq'},
                    'source': {'system': 'rgb', 'transfer': 'pq', 'primaries': 'bt2020',
                               'range': 'full', 'bit_depth': 10, 'layout': 'c3-f32le', 'orientation': 'top-left',
                               'mastering': {'min_nits': 0, 'max_nits': 10000, 'primaries': BT2020}},
                    'target': {'id': 'bt2020-10000', 'min_nits': 0, 'max_nits': 10000, 'primaries': BT2020},
                    'metadata': None}
        self.path = self.root / 'input.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.obj))

    def reject(self):
        self.save()
        with self.assertRaises(ValueError):
            input_manifest(self.path)

    def test_valid_public_fixture(self):
        obj, p, meta = input_manifest(self.path)
        self.assertIsNone(meta)
        self.assertEqual(p.read_bytes(), (self.root / 'input.f32').read_bytes())
        self.assertEqual(alignment(obj)['frame_index'], 1)

    def test_missing_and_wrong_hash(self):
        self.obj['frame']['input']['sha256'] = '0' * 64
        self.reject()
        self.obj['frame']['input']['file'] = 'absent'
        self.reject()

    def test_exact_byte_count_and_nonfinite(self):
        for data in (b'\x00', struct.pack('<12f', *([math.nan] * 12)), struct.pack('<12f', *([1.1] * 12))):
            (self.root / 'input.f32').write_bytes(data)
            self.obj['frame']['input']['sha256'] = hashlib.sha256(data).hexdigest()
            self.reject()

    def test_source_interpretation(self):
        for field, value in (('transfer', 'hlg'), ('primaries', 'p3'), ('range', 'auto'),
                             ('system', 'unknown'), ('orientation', 'bottom-left'), ('bit_depth', 9)):
            orig = self.obj['source'][field]
            self.obj['source'][field] = value
            self.reject()
            self.obj['source'][field] = orig

    def test_unknown_duplicate_and_boolean(self):
        self.obj['ignored_trim'] = 1
        self.reject()
        self.path.write_text('{"schema":1,"schema":1}')
        with self.assertRaises(ValueError):
            load_json(self.path)
        del self.obj['ignored_trim']
        self.obj['frame']['width'] = True
        self.reject()

    def test_target_validation(self):
        for field, value in (('max_nits', 0), ('min_nits', 10000), ('primaries', [0.3, 0.3] * 4)):
            orig = self.obj['target'][field]
            self.obj['target'][field] = value
            self.reject()
            self.obj['target'][field] = orig

    def test_no_fabricated_metadata(self):
        self.obj['source']['system'] = 'dolbyvision'
        self.reject()  # metadata absent; never silently render an HDR10 fallback
        self.obj['metadata'] = {'export': {'file': 'absent', 'sha256': '0' * 64},
                                'rpu': {'file': 'absent', 'sha256': '0' * 64},
                                'origin': 'synthetic', 'frame_index': 1, 'pts': {'num': 1, 'den': 24}}
        self.reject()
        self.obj['metadata']['origin'] = 'owned-real-content'
        self.obj['metadata']['frame_index'] = 2
        self.reject()

    def result(self, role, name):
        r = {'schema': 1, 'role': role, 'alignment': alignment(self.obj), 'encoding': ENCODING,
             'output': self.obj['frame']['input'], 'provenance': {'kind': 'public test fixture'}}
        path = self.root / name
        path.write_text(json.dumps(r))
        return path, r

    def test_reference_absent_misaligned_and_encoding(self):
        ca, _ = self.result('candidate', 'candidate.json')
        re, obj = self.result('reference', 'reference.json')
        obj['alignment']['pts']['num'] = 2
        re.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            compare(ca, re)
        obj['encoding'] = dict(ENCODING, transfer='linear')
        re.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            result_manifest(re)
        re.unlink()
        with self.assertRaises(OSError):
            compare(ca, re)

    def test_identical_reference_statistics(self):
        ca, _ = self.result('candidate', 'candidate.json')
        re, _ = self.result('reference', 'reference.json')
        self.assertEqual(compare(ca, re)['statistics']['max'], 0)

    def test_native_cpu_render_alignment_and_repeatability(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'native binary must be supplied for the approved complete batch')
        a = render(self.path, native, self.root / 'first')
        b = render(self.path, native, self.root / 'second')
        ra, pa = result_manifest(a)
        rb, pb = result_manifest(b)
        self.assertEqual(ra['alignment'], alignment(self.obj))
        self.assertEqual(ra['output']['sha256'], rb['output']['sha256'])
        self.assertEqual(pa, pb)
        self.assertIn('llvmpipe', ra['provenance']['device'])
        source = result_manifest(self.result('reference', 'reference.json')[0])[1]
        # Asymmetric 2x2 data catches channel/row flips, not just grey identity.
        for got, expected in zip(pa, source):
            for x, y in zip(got, expected):
                self.assertAlmostEqual(x, y, delta=0.00002)
        with self.assertRaises(ValueError):
            render(self.path, native, self.root / 'first')

    def test_native_limited_10bit_rgb_and_yuv(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'complete native batch requires compiled binary')
        self.obj['source']['range'] = 'limited'
        codes = (256, 512, 768, 876)
        for system in ('rgb', 'bt2020nc'):
            self.obj['source']['system'] = system
            triples = [(n / 1023,) * 3 if system == 'rgb' else (n / 1023, 512 / 1023, 512 / 1023)
                       for n in codes]
            raw = b''.join(struct.pack('<fff', *p) for p in triples)
            (self.root / 'input.f32').write_bytes(raw)
            self.obj['frame']['input']['sha256'] = hashlib.sha256(raw).hexdigest()
            self.save()
            receipt = render(self.path, native, self.root / system)
            _, output = result_manifest(receipt)
            for pixel, code in zip(output, codes):
                for channel in pixel:
                    self.assertAlmostEqual(channel, (code - 64) / 876, delta=0.00003)

    def test_native_target_peak_mapping(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'complete native batch requires compiled binary')
        raw = struct.pack('<12f', *([0.9] * 12))
        (self.root / 'input.f32').write_bytes(raw)
        self.obj['frame']['input']['sha256'] = hashlib.sha256(raw).hexdigest()
        for peak in (300, 616, 1000):
            self.obj['target'].update(id='synthetic-' + str(peak), max_nits=peak)
            self.save()
            receipt = render(self.path, native, self.root / str(peak))
            r, output = result_manifest(receipt)
            self.assertEqual(r['alignment']['target'], self.obj['target'])
            for pixel in output:
                for channel in pixel:
                    self.assertLessEqual(pq_eotf(channel), peak + 0.1)


if __name__ == '__main__':
    unittest.main()
