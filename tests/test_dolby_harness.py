"""Deferred stage-1 regression batch. Native tests require HDR_HARNESS_NATIVE.

No Dolby metadata is generated, not even an identity RPU. Metadata validation
cases exercise missing/mismatched/rejected inputs before any reshaping data.
"""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness.contracts import ENCODING, alignment, input_manifest, load_json, result_manifest
from tools.dolby_harness.harness import baseline_semantics, compare, control, render
from tools.dolby_harness.metric import compare_pixels, delta_itp, pq_eotf, pq_inverse, rgb_to_itp, summarize
from tools.dolby_harness.provenance import (FRONTEND_INPUTS, ROOT,
                                           implementation, native_environment)

BT2020 = [0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290]
BT709 = [0.640, 0.330, 0.300, 0.600, 0.150, 0.060, 0.3127, 0.3290]


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
        # Annex 4 supplies the codes; Annex 1 supplies the normative arithmetic.
        # Its informative rounded ITP example is not a precise numeric oracle.
        # Independently derived at 80/120 decimal digits (no metric imports):
        # evidence/dolby-harness-annex4-oracle.py and its JSON receipt.
        itp = rgb_to_itp((296 / 1023, 201 / 1023, 582 / 1023))
        expected = (0.3557205250540512, 0.1346466873449306, -0.1613950695752067)
        for got, target in zip(itp, expected):
            self.assertAlmostEqual(got, target, delta=1e-12)

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

    def samples(self, triples):
        raw = b''.join(struct.pack('<fff', *p) for p in triples)
        (self.root / 'input.f32').write_bytes(raw)
        self.obj['frame']['input']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.save()

    def native(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'complete approved batch requires compiled native binary')
        assert native is not None
        return Path(native)

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

    def test_reference_identity_mismatch_table(self):
        ca, _ = self.result('candidate', 'candidate.json')
        re, original = self.result('reference', 'reference.json')
        cases = [('target', dict(original['alignment']['target'], max_nits=616)),
                 ('source', dict(original['alignment']['source'], range='limited')),
                 ('source_sha256', '1' * 64), ('metadata_sha256', '2' * 64),
                 ('rpu_sha256', '3' * 64)]
        # Metadata hashes here are INVALID non-Dolby identities, not fake RPU data.
        for field, value in cases:
            with self.subTest(field=field):
                obj = copy.deepcopy(original)
                obj['alignment'][field] = value
                re.write_text(json.dumps(obj))
                with self.assertRaises(ValueError):
                    compare(ca, re)

    def test_comparison_snapshot_and_implementation_provenance(self):
        ca, candidate = self.result('candidate', 'candidate.json')
        re, reference = self.result('reference', 'reference.json')
        reference['provenance'] = {'renderer': 'PUBLIC fixture writer v1',
                                   'options': {'conversion': 'none', 'purpose': 'synthetic unit'}}
        re.write_text(json.dumps(reference, indent=3) + '\n')
        snapshots = {p: p.read_bytes() for p in (ca, re)}
        reads = {p: 0 for p in snapshots}
        read_bytes = Path.read_bytes

        def once(path):
            if path in snapshots:
                reads[path] += 1
                self.assertEqual(reads[path], 1, 'manifest must be parsed from hashed snapshot')
                return snapshots[path]
            return read_bytes(path)

        with patch.object(Path, 'read_bytes', once):
            report = compare(ca, re)
        p = report['provenance']
        for role, path in (('candidate', ca), ('reference', re)):
            self.assertEqual(p[role + '_manifest_sha256'], hashlib.sha256(snapshots[path]).hexdigest())
        self.assertEqual(p['candidate_renderer'], candidate['provenance'])
        self.assertEqual(p['reference_renderer'], reference['provenance'])
        self.assertEqual(set(p['comparator']['sources']), set(FRONTEND_INPUTS))
        changed = copy.deepcopy(reference)
        changed['provenance']['options']['conversion'] = 'different-public-option'
        re.write_text(json.dumps(changed))
        self.assertNotEqual(compare(ca, re)['provenance']['reference_manifest_sha256'],
                            p['reference_manifest_sha256'])

    def test_environment_and_frontend_tamper(self):
        inherited = {'LD_PRELOAD': '/absent', 'LD_LIBRARY_PATH': '/absent',
                     'VK_DRIVER_FILES': '/wrong', 'VK_LAYER_PATH': '/wrong',
                     'VK_INSTANCE_LAYERS': 'wrong', 'MESA_LOADER_DRIVER_OVERRIDE': 'wrong',
                     'HOME': '/wrong', 'PATH': '/wrong'}
        with patch.dict(os.environ, inherited):
            env = native_environment(self.root)
        self.assertEqual(env['VK_DRIVER_FILES'], '/usr/share/vulkan/icd.d/lvp_icd.json')
        self.assertEqual(env['VK_LOADER_LAYERS_DISABLE'], '~all~')
        self.assertEqual(env['HOME'], str(self.root))
        for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'VK_LAYER_PATH', 'VK_INSTANCE_LAYERS',
                    'MESA_LOADER_DRIVER_OVERRIDE'):
            self.assertNotIn(key, env)
        read_bytes = Path.read_bytes

        def changed(path):
            data = read_bytes(path)
            return data + b'\n# tampered\n' if path == ROOT / FRONTEND_INPUTS[0] else data

        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'changed since import'):
                implementation()

    def test_requested_effective_semantics_annotation(self):
        self.obj['source']['mastering']['min_nits'] = 0.0004
        self.obj['target']['min_nits'] = 0.005
        self.save()
        obj, _, metadata = input_manifest(self.path)
        semantic = baseline_semantics(obj, metadata)
        self.assertEqual(semantic['pq_minima']['requested_target_nits'], 0.005)
        self.assertEqual(semantic['pq_minima']['effective_nominal_target_nits'], 1e-6)
        self.assertFalse(semantic['cie_y_l1']['recognized'])
        # Annotation only: real rendering still rejects Dolby without real metadata.
        obj['source'].update(system='dolbyvision', range='limited')
        self.assertEqual(baseline_semantics(obj, None)['range']['attested_base_layer_range'], 'limited')
        self.assertIn('RPU matrices', baseline_semantics(obj, None)['range']['effective_normalization'])

    def test_native_cpu_render_alignment_and_repeatability(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'native binary must be supplied for the approved complete batch')
        assert native is not None
        a = render(self.path, native, self.root / 'first')
        with patch.dict(os.environ, {'LD_PRELOAD': '/absent-public-test',
                                     'LD_LIBRARY_PATH': '/absent-public-test',
                                     'VK_DRIVER_FILES': '/absent-public-test',
                                     'VK_INSTANCE_LAYERS': 'nonexistent-public-layer'}):
            b = render(self.path, native, self.root / 'second')
        ra, pa = result_manifest(a)
        rb, pb = result_manifest(b)
        self.assertEqual(ra['alignment'], alignment(self.obj))
        self.assertEqual(ra['output']['sha256'], rb['output']['sha256'])
        self.assertEqual(pa, pb)
        self.assertIn('llvmpipe', ra['provenance']['device'])
        p = ra['provenance']
        self.assertEqual(p['execution']['native_sha256'], hashlib.sha256(Path(native).read_bytes()).hexdigest())
        self.assertEqual(p['input_manifest_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(p['execution']['frontend'], implementation())
        self.assertEqual(p['execution']['runtime'], p['execution']['compile_receipt']['runtime'])
        source = result_manifest(self.result('reference', 'reference.json')[0])[1]
        # Asymmetric 2x2 data catches channel/row flips, not just grey identity.
        for got, expected in zip(pa, source):
            for x, y in zip(got, expected):
                self.assertAlmostEqual(x, y, delta=0.00002)
        with self.assertRaises(ValueError):
            render(self.path, native, self.root / 'first')

    def test_native_limited_10bit_rgb(self):
        native = self.native()
        self.obj['source']['range'] = 'limited'
        codes = (256, 512, 768, 876)
        self.samples([(n / 1023,) * 3 for n in codes])
        _, output = result_manifest(render(self.path, native, self.root / 'limited-rgb'))
        for pixel, code in zip(output, codes):
            for channel in pixel:
                self.assertAlmostEqual(channel, (code - 64) / 876, delta=0.00003)

    def test_native_chromatic_bt2020nc_full_limited_depths(self):
        native = self.native()
        # ITU-R BT.2020 NC: Kr=.2627, Kb=.0593, Kg=1-Kr-Kb.
        # Independent digital-code/range oracle (not generated from renderer output).
        # Full chroma uses the pinned baseline's MAX_INT=1 convention: midpoint
        # 2^(b-1), positive half-range MAX_INT-midpoint; limited is 16/219/224.
        kr, kb = 0.2627, 0.0593
        kg = 1 - kr - kb
        codes8 = ((96, 144, 112), (128, 108, 148), (152, 140, 120), (112, 116, 136))
        for depth in (8, 10, 12, 16):
            scale, maximum = 2 ** (depth - 8), 2 ** depth - 1
            codes = [tuple(c * scale for c in p) for p in codes8]
            for levels in ('full', 'limited'):
                with self.subTest(depth=depth, levels=levels):
                    self.obj['source'].update(system='bt2020nc', range=levels, bit_depth=depth)
                    self.samples([tuple(c / maximum for c in p) for p in codes])
                    _, output = result_manifest(render(self.path, native, self.root / f'yuv-{depth}-{levels}'))
                    for got, (yc, cb, cr) in zip(output, codes):
                        y = yc / maximum if levels == 'full' else (yc - 16 * scale) / (219 * scale)
                        denom = 2 * (maximum - 128 * scale) if levels == 'full' else 224 * scale
                        u, v = (cb - 128 * scale) / denom, (cr - 128 * scale) / denom
                        r, b = y + 2 * (1 - kr) * v, y + 2 * (1 - kb) * u
                        g = (y - kr * r - kb * b) / kg
                        expected = (r, g, b)
                        self.assertGreater(min(expected), 0.05)
                        self.assertLess(max(expected), 0.85)
                        for x, target in zip(got, expected):
                            self.assertAlmostEqual(x, target, delta=0.00004)

    def test_native_target_peak_mapping(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'complete native batch requires compiled binary')
        self.samples([(0.9,) * 3] * 4)
        mapped = []
        for peak in (300, 616, 1000):
            self.obj['target'].update(id='synthetic-' + str(peak), max_nits=peak)
            self.save()
            receipt = render(self.path, native, self.root / str(peak))
            r, output = result_manifest(receipt)
            self.assertEqual(r['alignment']['target'], self.obj['target'])
            for pixel in output:
                for channel in pixel:
                    self.assertGreater(pq_eotf(channel), peak * 0.5)
                    self.assertLessEqual(pq_eotf(channel), peak + 0.1)
            mapped.append(pq_eotf(output[0][0]))
        self.assertGreater(mapped[1] - mapped[0], 100)
        self.assertGreater(mapped[2] - mapped[1], 100)

    def test_native_narrow_gamut_preserves_encoding(self):
        native = self.native()
        # D65 linear BT.709->BT.2020 matrix, independent colourimetry oracle.
        # This asymmetric point is well inside the narrower target volume.
        matrix = ((0.627404, 0.329283, 0.043313),
                  (0.069097, 0.919540, 0.011362),
                  (0.016391, 0.088013, 0.895595))
        inside = tuple(pq_inverse(sum(a * b for a, b in zip(row, (20, 40, 30))))
                       for row in matrix)
        samples = [(0.5,) * 3, (0.65, 0.05, 0.05), inside, (0.5,) * 3]
        self.samples(samples)
        _, wide = result_manifest(render(self.path, native, self.root / 'wide'))
        self.obj['target'].update(id='PUBLIC-synthetic-bt709', primaries=BT709)
        self.save()
        receipt, narrow = result_manifest(render(self.path, native, self.root / 'narrow'))
        self.assertEqual(receipt['encoding'], ENCODING)  # still PQ BT.2020, not BT.709 labelled RGB
        self.assertEqual(receipt['alignment']['target']['primaries'], BT709)
        for index in (0, 2, 3):
            for got, expected in zip(narrow[index], samples[index]):
                self.assertAlmostEqual(got, expected, delta=0.00004)
        self.assertGreater(max(abs(a - b) for a, b in zip(narrow[1], wide[1])), 0.002)
        self.assertGreater(max(narrow[1]), 0.3)  # not black in place of gamut mapping

    def test_native_positive_min_is_ignored_baseline(self):
        native = self.native()
        self.samples([(pq_inverse(n),) * 3 for n in (0.00001, 0.0001, 1, 100)])
        _, zero = result_manifest(render(self.path, native, self.root / 'zero-min'))
        self.obj['source']['mastering']['min_nits'] = 0.0004
        self.obj['target']['min_nits'] = 0.0004
        self.save()
        receipt, positive = result_manifest(render(self.path, native, self.root / 'positive-min'))
        self.assertEqual(receipt['provenance']['baseline_semantics']['pq_minima']['requested_target_nits'], 0.0004)
        for a, b in zip(zero, positive):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, delta=0.00002)
        self.assertLess(pq_eotf(positive[0][0]), 0.0004)  # no fabricated requested black floor
        self.assertAlmostEqual(pq_eotf(positive[-1][0]), 100, delta=0.2)

    def test_native_rejects_controls_and_pixels_without_output(self):
        native = self.native()
        valid_control = control(self.obj, None)
        valid_pixels = (self.root / 'input.f32').read_bytes()
        tokens = valid_control.split()
        malformed = tokens.copy()
        malformed[1] = '2oops'
        cases = [('magic', valid_control.replace('DVH1', 'BAD', 1), valid_pixels),
                 ('malformed', ' '.join(malformed), valid_pixels),
                 ('trailing', valid_control + 'unexpected\n', valid_pixels),
                 ('truncated-control', ' '.join(tokens[:-1]), valid_pixels),
                 ('short-pixels', valid_control, valid_pixels[:-1]),
                 ('trailing-pixels', valid_control, valid_pixels + b'\x00')]
        for name, value in (('nan', math.nan), ('negative', -0.1), ('above-one', 1.1)):
            cases.append((name, valid_control, struct.pack('<f', value) + valid_pixels[4:]))
        for name, text, data in cases:
            with self.subTest(case=name):
                ctl, inp, out = [self.root / (name + suffix) for suffix in ('.ctl', '.f32', '.out')]
                ctl.write_text(text)
                inp.write_bytes(data)
                run = subprocess.run([str(native), str(ctl), str(inp), str(out)],
                                     env=native_environment(self.root), capture_output=True, timeout=30)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse(out.exists())

    def test_native_provenance_rejects_elf_source_and_runtime_tamper(self):
        native = self.native()
        original = json.loads((native.parent / 'compile-receipt.json').read_bytes())
        cases = [('binary', ('binary_sha256',), '0' * 64),
                 ('source', ('sources', 'tools/dolby_harness/headless_render.c'), '1' * 64),
                 ('runtime', ('runtime', '/usr/share/vulkan/icd.d/lvp_icd.json'), '2' * 64)]
        for name, keys, value in cases:
            with self.subTest(case=name):
                receipt = copy.deepcopy(original)
                obj = receipt
                for key in keys[:-1]:
                    obj = obj[key]
                obj[keys[-1]] = value
                path = self.root / (name + '-receipt.json')
                path.write_text(json.dumps(receipt))
                output = self.root / (name + '-render')
                with self.assertRaises(ValueError):
                    render(self.path, native, output, path)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
