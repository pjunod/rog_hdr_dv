"""Deferred post-reshape tests; positives consume the real private official corpus.

No proprietary fixture, invented RPU or replacement positive metadata is public.
Mutations of copied authentic artifacts are rejection controls, never official
references. Require durable task-owned temporary storage, not system /tmp.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.dolby_harness.contracts import alignment, input_manifest, result_manifest
from tools.dolby_harness.harness import baseline_semantics, compare, control, render
from tools.dolby_harness.postreshape import NAMESPACE, parsed_export


class PostreshapeTests(unittest.TestCase):
    def setUp(self):
        corpus = os.environ.get('HDR_POSTRESHAPE_CORPUS')
        temporary = os.environ.get('HDR_POSTRESHAPE_TMP')
        self.assertIsNotNone(corpus, 'real privately retained official corpus required')
        self.assertIsNotNone(temporary, 'durable task-owned temporary parent required')
        assert corpus is not None and temporary is not None
        parent = Path(temporary).resolve()
        self.assertTrue(parent.is_dir())
        self.assertFalse(any(parent == Path(p) or Path(p) in parent.parents
                             for p in ('/tmp', '/private/tmp', '/var/tmp')))
        self.tmp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'corpus'
        shutil.copytree(corpus, self.root)
        self.path = self.root / 'panel616/frame-1.json'
        self.obj = json.loads(self.path.read_bytes())
        self.analysis = self.root / 'analysis.xml'
        self.sequence = self.root / 'source-manifest.json'
        self.export = self.root / 'export-1.json'

    def save(self):
        self.path.write_text(json.dumps(self.obj))

    def rebind(self, key, path):
        self.obj['metadata'][key]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.save()

    def rejects(self):
        self.save()
        with self.assertRaises(ValueError):
            input_manifest(self.path)

    def xml_mutation(self, mutate):
        root = ET.fromstring(self.analysis.read_bytes())
        mutate(root)
        self.analysis.write_bytes(ET.tostring(root))
        self.rebind('analysis', self.analysis)
        self.rejects()

    def find(self, node, path):
        found = node.find('/'.join('{' + NAMESPACE + '}' + part for part in path.split('/')))
        self.assertIsNotNone(found)
        assert found is not None
        return found

    def test_genuine_frame_local_l1_and_boundaries(self):
        for i in range(6):
            with self.subTest(frame=i):
                obj, _, data = input_manifest(self.root / f'panel616/frame-{i}.json')
                mapping = data['mapping']
                self.assertEqual(mapping['shot_in'] + mapping['edit_offset'], i)
                self.assertEqual(data['translation'], 'dolby-xml-l1-direct-v1')
                self.assertEqual(data['max_pq_y'], data['l1']['max_pq'])
                self.assertEqual(data['avg_pq_y'], data['l1']['avg_pq'])
                self.assertNotIn('rpu_sha256', alignment(obj, data))
        _, _, first = input_manifest(self.root / 'panel616/frame-0.json')
        _, _, second = input_manifest(self.path)
        self.assertEqual(first['mapping']['shot_id'], second['mapping']['shot_id'])
        self.assertNotEqual(first['l1']['avg_pq'], second['l1']['avg_pq'])

    def test_rgb_control_contains_l1_without_reshape(self):
        obj, _, data = input_manifest(self.path)
        tokens = control(obj, data).split()
        self.assertEqual(tokens[3], '0')
        self.assertEqual(len(tokens), 28)
        self.assertEqual(float(tokens[-2]), data['l1']['max_pq'])
        self.assertEqual(float(tokens[-1]), data['l1']['avg_pq'])
        semantics = baseline_semantics(obj, data)
        self.assertTrue(semantics['cie_y_l1']['recognized'])
        self.assertEqual(semantics['post_reshape']['raw_l1'], data['l1'])
        # Zero is an arithmetic fallback control, not invented official output.
        zero = copy.deepcopy(data)
        zero['max_pq_y'] = zero['avg_pq_y'] = 0
        self.assertFalse(baseline_semantics(obj, zero)['cie_y_l1']['recognized'])

    def test_required_schema_stage_source_and_metadata(self):
        original = copy.deepcopy(self.obj)
        mutations = [('schema', True), ('schema', 1), ('stage', 'consumer-rpu'), ('metadata', None)]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                self.obj = copy.deepcopy(original)
                self.obj[key] = value
                self.rejects()
        for key, value in [('system', 'dolbyvision'), ('system', 'bt2020nc'), ('range', 'limited')]:
            self.obj = copy.deepcopy(original)
            self.obj['source'][key] = value
            self.rejects()

    def test_artifact_hash_and_missing_input(self):
        original = copy.deepcopy(self.obj)
        for key in ('analysis', 'export', 'source_manifest'):
            for field, value in [('sha256', '0' * 64), ('file', 'absent')]:
                with self.subTest(key=key, field=field):
                    self.obj = copy.deepcopy(original)
                    self.obj['metadata'][key][field] = value
                    self.rejects()

    def test_export_cannot_override_raw_l1_parser_or_mapping(self):
        raw = json.loads(self.export.read_bytes())
        for mutate in (lambda x: x['l1'].update(avg_pq=0),
                       lambda x: x['parser'].update(sha256='0'*64),
                       lambda x: x['mapping'].update(edit_offset=0),
                       lambda x: x.update(source_sha256='0'*64),
                       lambda x: x.update(analysis_version=True),
                       lambda x: x.update(rpu_sha256='0'*64)):
            data = copy.deepcopy(raw)
            mutate(data)
            self.export.write_text(json.dumps(data))
            self.rebind('export', self.export)
            self.rejects()

    def test_exact_pts_and_sequence_association(self):
        original = copy.deepcopy(self.obj)
        self.obj['frame']['pts']['num'] += 1
        self.obj['metadata']['pts'] = copy.deepcopy(self.obj['frame']['pts'])
        self.rejects()
        self.obj = original
        data = json.loads(self.sequence.read_bytes())
        data['frames'][1]['normalized'] = copy.deepcopy(data['frames'][0]['normalized'])
        self.sequence.write_text(json.dumps(data))
        self.rebind('source_manifest', self.sequence)
        self.rejects()

    def test_duplicate_frame_rejected(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            shot.append(copy.deepcopy(self.find(shot, 'Frame')))
        self.xml_mutation(mutate)

    def test_missing_frame_l1_never_inherits_shot_l1(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            frame = shot.findall('{' + NAMESPACE + '}Frame')[1]
            dynamic = self.find(frame, 'PluginNode/DVDynamicData')
            dynamic.remove(self.find(dynamic, 'Level1'))
        self.xml_mutation(mutate)

    def test_overlap_and_offset_boundary_rejected(self):
        pristine = self.analysis.read_bytes()
        for field, value in [('In', '2'), ('Duration', '0')]:
            self.analysis.write_bytes(pristine)
            def mutate(root):
                shots = self.find(root, 'Outputs/Output/Video/Track').findall('{' + NAMESPACE + '}Shot')
                self.find(shots[1], 'Record/' + field).text = value
            self.xml_mutation(mutate)
        self.analysis.write_bytes(pristine)
        def mutate(root):
            self.find(root, 'Outputs/Output/Video/Track/Shot/Frame/EditOffset').text = '3'
        self.xml_mutation(mutate)

    def test_namespace_multitrack_and_l9_rejected(self):
        pristine = self.analysis.read_bytes()
        self.analysis.write_bytes(pristine.replace(NAMESPACE.encode(), b'urn:not-official'))
        self.rebind('analysis', self.analysis)
        self.rejects()
        for mode in ('track', 'l9'):
            self.analysis.write_bytes(pristine)
            def mutate(root):
                if mode == 'track':
                    video = self.find(root, 'Outputs/Output/Video')
                    video.append(copy.deepcopy(self.find(video, 'Track')))
                else:
                    self.find(root, 'Outputs/Output/Video/Track/Shot/PluginNode/DVDynamicData/Level9/SourceColorPrimary').text = '0 0 0 0 0 0 0 0'
            self.xml_mutation(mutate)

    def test_missing_malformed_and_zero_l1_controls(self):
        # Deliberately altered raw XML is a parser/control test only; it is not
        # exported as an official reference or passed to a native fidelity run.
        obj, _, _ = input_manifest(self.path)
        original = self.analysis.read_bytes()
        for text_value in ('0 0', '0 nan 1', '0 1 0', '0 0 0'):
            root = ET.fromstring(original)
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            frame = shot.findall('{' + NAMESPACE + '}Frame')[1]
            self.find(frame, 'PluginNode/DVDynamicData/Level1/ImageCharacter').text = text_value
            raw = ET.tostring(root)
            if text_value == '0 0 0':
                data = parsed_export(raw, self.sequence, self.sequence.read_bytes(), obj)
                self.assertEqual(data['l1'], {'min_pq': 0, 'avg_pq': 0, 'max_pq': 0})
            else:
                with self.assertRaises(ValueError):
                    parsed_export(raw, self.sequence, self.sequence.read_bytes(), obj)

    def test_genuine_metadata_native_execution_and_result_alignment(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'retained source-bound native ELF required')
        assert native is not None
        result = render(self.path, native, self.root / 'native-candidate')
        obj, _ = result_manifest(result)
        self.assertEqual(obj['schema'], 2)
        semantics = obj['provenance']['baseline_semantics']
        self.assertTrue(semantics['cie_y_l1']['recognized'])
        _, _, meta = input_manifest(self.path)
        for key in ('max_pq_y', 'avg_pq_y'):
            self.assertEqual(semantics['cie_y_l1']['native_' + key], struct.unpack('<f', struct.pack('<f', meta[key]))[0])
        reference = self.root / 'panel616/reference-1.json'
        official, _ = result_manifest(reference)
        self.assertEqual(official['alignment'], obj['alignment'])
        # No numerical baseline here: deliberately mismatch before comparison.
        official['alignment']['mapping']['shot_id'] += '-wrong'
        reference.write_text(json.dumps(official))
        with self.assertRaises(ValueError):
            compare(result, reference)

    def test_result_schema_stage_encoding_and_mapping_mixing(self):
        path = self.root / 'panel616/reference-1.json'
        original = json.loads(path.read_bytes())
        mutations = [lambda x: x.update(schema=1),
                     lambda x: x['alignment'].update(stage='consumer-rpu'),
                     lambda x: x['encoding'].update(primaries='p3'),
                     lambda x: x['alignment']['mapping'].update(edit_offset=3),
                     lambda x: x['alignment'].update(rpu_sha256='0'*64),
                     lambda x: x['alignment']['mapping']['edit_rate'].update(num=True)]
        for mutate in mutations:
            obj = copy.deepcopy(original)
            mutate(obj)
            path.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                result_manifest(path)


if __name__ == '__main__':
    unittest.main()
