"""Deferred genuine original-target identity regressions; no vendor invocation.

Requires additive current-parser manifests. Historical results stay on their
executing frontend; neither acquisition nor render nor comparison runs here.
"""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import authored_master as am, open_dm as dm
from tools.dolby_harness.contracts import input_manifest


class OriginalTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(os.environ['HDR_AUTHORED_INPUT1200'])
        cls.obj, _, cls.meta = input_manifest(cls.path)
        cls.base = cls.path.parent
        cls.root = am.document(am.snapshot(cls.base, cls.obj['metadata']['analysis'])[1])
        cls.receipt = json.loads(am.snapshot(cls.base, cls.obj['metadata']['declaration_repair'])[1])

    def check_receipt(self, receipt, directory):
        raw = json.dumps(receipt).encode()
        path = Path(directory) / 'rejection-only-receipt.json'
        path.write_bytes(raw)
        return am.reference_provenance(self.base, {'file': str(path), 'sha256': am.sha(raw)},
            self.obj, {**self.meta, 'declaration_repair_sha256': am.sha(raw)},
            {'file': receipt['Mac_reference']['path'], 'sha256': receipt['Mac_reference']['sha256']})

    def test_original48_source283_global1200_control_and_reference(self):
        self.assertEqual(self.obj['frame']['index'], 1200)
        m = self.meta['mapping']
        self.assertEqual((m['shot_id'], m['source_parent_id']),
            ('5513873e-6e64-48a2-9b02-0ec5e4e781f6', '23ed4d2b-bb33-480b-9ac0-cedd5118d487'))
        self.assertEqual((m['shot_in'], m['edit_offset'], m['source_in']), (917, 283, 0))
        self.assertEqual((m['selection_kind'], m['frame_id']), ('shot-inherited', None))
        self.assertEqual(self.obj['target'], {'id': '48', 'min_nits': 0.0, 'max_nits': 1000.0, 'primaries': am.P3})
        a = dm.algorithm(self.obj, self.meta, dm.SQRTSUM_VARIANT)
        self.assertEqual(a['original_trim'], '0,0,0,-0.008,0,0.013,-0.012,0,-0.75')
        self.assertEqual(a['prepared_curve']['target_display_nits'], [0, 1000])
        self.assertEqual(dm.control(self.obj, self.meta, dm.SQRTSUM_VARIANT).split()[:5],
                         ['DVH4', '4096', '2160', '1', '48'])
        self.assertEqual(a['target_description_id'], 48)
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn('frame1200 only', self.check_receipt(self.receipt, directory)['content_limit'])

    def test_target27_metadata_and_legacy_protocol_unchanged(self):
        obj, _, meta = input_manifest(Path(os.environ['HDR_AUTHORED_INPUT']))
        self.assertEqual(obj['target']['id'], '27')
        a = dm.algorithm(obj, meta, dm.SQRTSUM_VARIANT)
        self.assertEqual(a['target_description_id'], 27)
        self.assertEqual(a['prepared_curve']['target_display_nits'], [0, 600])
        self.assertEqual(dm.control(obj, meta, dm.SQRTSUM_VARIANT).split()[4], '27')
        self.assertEqual(dm.control(obj, meta, dm.Y_VARIANT).split()[:4], ['DVH3', '4096', '2160', '1'])
        for variant in dm.VARIANTS:
            if variant != dm.SQRTSUM_VARIANT:
                with self.assertRaisesRegex(ValueError, 'only exact original target27'):
                    dm.algorithm(self.obj, self.meta, variant)

    def test_noncanonical_id_volume_and_original_declaration_rejections(self):
        for token in ('048', '+48', '48.0', ' 48', '0', '65536', True, 48):
            obj = copy.deepcopy(self.obj)
            obj['target']['id'] = token
            with self.subTest(token=token), self.assertRaises(ValueError):
                dm.algorithm(obj, self.meta, dm.SQRTSUM_VARIANT)
        for key, value in (('min_nits', 1), ('max_nits', 600), ('primaries', [0.7] * 8)):
            target = copy.deepcopy(self.obj['target'])
            target[key] = value
            with self.assertRaises(ValueError):
                am.target_declaration(self.root, target)
        node = am.target_declaration(self.root, self.obj['target'])
        root = copy.deepcopy(self.root)
        _, track = am.track(root)
        am.one(am.one(am.one(track, 'PluginNode'), 'DolbyEDR'), 'Characteristics').append(copy.deepcopy(node))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            am.target_declaration(root, self.obj['target'])

    def test_missing_conflicting_and_ambiguous_selected_trim(self):
        for mode in ('absent', 'conflict', 'field'):
            meta = copy.deepcopy(self.meta)
            selected = [r for r in meta['records'] if r['level'] == 2 and r['target_id'] == 48]
            if mode == 'absent':
                meta['records'] = [r for r in meta['records'] if r not in selected]
            elif mode == 'conflict':
                other = copy.deepcopy(selected[0])
                next(f for f in other['fields'] if f['name'] == 'Trim')['text'] = '0,0,0,0,0,0,0,0,0'
                meta['records'].append(other)
            else:
                selected[0]['fields'].append(copy.deepcopy(next(f for f in selected[0]['fields'] if f['name'] == 'Trim')))
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                dm.algorithm(self.obj, meta, dm.SQRTSUM_VARIANT)

    def test_reference_id_volume_argv_and_source_rejections(self):
        cases = [lambda r: r['target'].update(target_id=27),
                 lambda r: r['target']['exact_original_tuple'].update(PeakBrightness='600'),
                 lambda r: r['render']['argv'].__setitem__(14, '27'),
                 lambda r: r['render']['argv'].__setitem__(-1, '283'),
                 lambda r: r['frame_binding'].update(index=283)]
        with tempfile.TemporaryDirectory() as directory:
            for mutate in cases:
                receipt = copy.deepcopy(self.receipt)
                mutate(receipt)
                with self.assertRaises(ValueError):
                    self.check_receipt(receipt, directory)

    def test_actual_target_info_and_render_log_mismatch_or_duplicates(self):
        for request_id, field in ((self.receipt['target_info_request'], 'target info'),
                                  (self.receipt['render_request'], 'Target Display')):
            entry = next(e for e in self.receipt['requests'] if e['request_id'] == request_id)['full_output']
            original = am.retained(self.base, entry)[1]
            node = am.target_declaration(self.root, self.obj['target'])
            am.target_log(original.decode(), field, node, self.obj['target'])
            for before, after in ((b'(ID 48)', b'(ID 27)'),
                                  (b'pq(0,1000)', b'pq(0,600)'),
                                  (b'rgb computer p3d65', b'rgb computer bt2020')):
                self.assertIn(before, original)
                with self.assertRaises(ValueError):
                    am.target_log(original.replace(before, after).decode(), field, node, self.obj['target'])
            with self.assertRaises(ValueError):
                am.target_log((original + original).decode(), field, node, self.obj['target'])


if __name__ == '__main__':
    unittest.main()
