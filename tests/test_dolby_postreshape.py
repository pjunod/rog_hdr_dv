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

    def rejects(self, diagnostic):
        self.save()
        with self.assertRaisesRegex(ValueError, diagnostic):
            input_manifest(self.path)

    def parse_control(self, raw, obj=None, sequence_raw=None):
        # Direct parser entry: no stale export can mask a structural failure.
        return parsed_export(raw, self.sequence,
                             self.sequence.read_bytes() if sequence_raw is None else sequence_raw,
                             self.obj if obj is None else obj)

    def parser_rejects(self, raw, diagnostic, obj=None, sequence_raw=None):
        with self.assertRaisesRegex(ValueError, diagnostic):
            self.parse_control(raw, obj, sequence_raw)

    def xml_mutation(self, mutate, diagnostic):
        root = ET.fromstring(self.analysis.read_bytes())
        mutate(root)
        self.parser_rejects(ET.tostring(root), diagnostic)

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
        mutations = [('schema', True, 'unknown harness schema'),
                     ('schema', 1, 'missing or unknown contract fields'),
                     ('stage', 'consumer-rpu', 'unknown display-management stage'),
                     ('metadata', None, 'missing or unknown contract fields')]
        for key, value, diagnostic in mutations:
            with self.subTest(key=key, value=value):
                self.obj = copy.deepcopy(original)
                self.obj[key] = value
                self.rejects(diagnostic)
        for key, value in [('system', 'dolbyvision'), ('system', 'bt2020nc'), ('range', 'limited')]:
            self.obj = copy.deepcopy(original)
            self.obj['source'][key] = value
            self.rejects('post-reshape requires explicit full-range RGB PQ')

    def test_artifact_hash_and_missing_input(self):
        original = copy.deepcopy(self.obj)
        for key in ('analysis', 'export', 'source_manifest'):
            for field, value in [('sha256', '0' * 64), ('file', 'absent')]:
                with self.subTest(key=key, field=field):
                    self.obj = copy.deepcopy(original)
                    self.obj['metadata'][key][field] = value
                    self.rejects('input SHA256 mismatch' if field == 'sha256' else 'input absent')

    def test_export_cannot_override_raw_l1_parser_or_mapping(self):
        raw = json.loads(self.export.read_bytes())
        mutations = [(lambda x: x['l1'].update(avg_pq=0), 'export differs from bound official XML'),
                     (lambda x: x['parser'].update(sha256='0'*64), 'export differs from bound official XML'),
                     (lambda x: x['mapping'].update(edit_offset=0), 'export differs from bound official XML'),
                     (lambda x: x.update(source_sha256='0'*64), 'export differs from bound official XML'),
                     (lambda x: x.update(analysis_sha256='0'*64), 'export differs from bound official XML'),
                     (lambda x: x.update(analysis_version=True), 'integer export schema/version required'),
                     (lambda x: x.update(rpu_sha256='0'*64), 'missing or unknown contract fields')]
        for mutate, diagnostic in mutations:
            data = copy.deepcopy(raw)
            mutate(data)
            self.export.write_text(json.dumps(data))
            self.rebind('export', self.export)
            self.rejects(diagnostic)

    def test_exact_pts_and_sequence_association(self):
        original = copy.deepcopy(self.obj)
        self.obj['frame']['pts']['num'] += 1
        self.obj['metadata']['pts'] = copy.deepcopy(self.obj['frame']['pts'])
        self.parser_rejects(self.analysis.read_bytes(), 'frame PTS does not match zero-origin XML timeline')
        self.rejects('frame PTS does not match zero-origin XML timeline')
        self.obj = original
        data = json.loads(self.sequence.read_bytes())
        data['frames'][1]['normalized'] = copy.deepcopy(data['frames'][0]['normalized'])
        self.sequence.write_text(json.dumps(data))
        self.rebind('source_manifest', self.sequence)
        self.parser_rejects(self.analysis.read_bytes(), 'frame not bound to analyzed sequence')
        self.rejects('frame not bound to analyzed sequence')

    def test_duplicate_frame_rejected(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            shot.append(copy.deepcopy(self.find(shot, 'Frame')))
        self.xml_mutation(mutate, 'duplicate or out-of-shot XML frame')

    def test_missing_frame_l1_never_inherits_shot_l1(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            frame = shot.findall('{' + NAMESPACE + '}Frame')[1]
            dynamic = self.find(frame, 'PluginNode/DVDynamicData')
            dynamic.remove(self.find(dynamic, 'Level1'))
        self.xml_mutation(mutate, 'missing or ambiguous XML Level1')

    def test_duplicate_selected_l1_rejected(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            frame = shot.findall('{' + NAMESPACE + '}Frame')[1]
            dynamic = self.find(frame, 'PluginNode/DVDynamicData')
            dynamic.append(copy.deepcopy(self.find(dynamic, 'Level1')))
        self.xml_mutation(mutate, 'missing or ambiguous XML Level1')

    def test_missing_selected_frame_rejected(self):
        def mutate(root):
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            shot.remove(shot.findall('{' + NAMESPACE + '}Frame')[1])
        self.xml_mutation(mutate, 'missing or ambiguous frame-local XML L1 mapping')

    def test_overlap_and_offset_boundary_rejected(self):
        for field, value, diagnostic in [('In', '2', 'overlapping'),
                                         ('Duration', '0', 'integer outside supported domain')]:
            def mutate(root):
                shots = self.find(root, 'Outputs/Output/Video/Track').findall('{' + NAMESPACE + '}Shot')
                self.find(shots[1], 'Record/' + field).text = value
            self.xml_mutation(mutate, diagnostic)
        def mutate(root):
            self.find(root, 'Outputs/Output/Video/Track/Shot/Frame/EditOffset').text = '3'
        self.xml_mutation(mutate, 'duplicate or out-of-shot XML frame')

    def test_namespace_multitrack_and_l9_rejected(self):
        pristine = self.analysis.read_bytes()
        self.parser_rejects(pristine.replace(NAMESPACE.encode(), b'urn:not-official'),
                            'only CM4 XML4.0.2 supported')
        for mode in ('track', 'l9'):
            def mutate(root):
                if mode == 'track':
                    video = self.find(root, 'Outputs/Output/Video')
                    video.append(copy.deepcopy(self.find(video, 'Track')))
                else:
                    self.find(root, 'Outputs/Output/Video/Track/Shot/PluginNode/DVDynamicData/Level9/SourceColorPrimary').text = '0 0 0 0 0 0 0 0'
            self.xml_mutation(mutate, 'missing or ambiguous XML Track' if mode == 'track'
                              else 'applicable L9/source declaration mismatch')

    def test_frame_l9_override_rejected(self):
        # Even an identical declaration is unsupported, not silently inherited.
        for index in (0, 1):
            with self.subTest(selected=index == 1):
                def mutate(root):
                    shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
                    frame = shot.findall('{' + NAMESPACE + '}Frame')[index]
                    dynamic = self.find(frame, 'PluginNode/DVDynamicData')
                    dynamic.append(copy.deepcopy(self.find(shot, 'PluginNode/DVDynamicData/Level9')))
                self.xml_mutation(mutate, 'frame-level L9 override unsupported')

    def test_harmless_utf8_reserialization(self):
        original = self.parse_control(self.analysis.read_bytes())
        root = ET.fromstring(self.analysis.read_bytes())
        ET.indent(root, space='  ')
        serialized = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        self.assertNotEqual(serialized, self.analysis.read_bytes())
        for raw in (serialized, b'\xef\xbb\xbf' + serialized):
            with self.subTest(bom=raw.startswith(b'\xef\xbb\xbf')):
                actual = self.parse_control(raw)
                expected = copy.deepcopy(original)
                expected['analysis_sha256'] = hashlib.sha256(raw).hexdigest()
                self.assertEqual(actual, expected)
                # Consistently rebound envelope/export accepts changed bytes.
                self.analysis.write_bytes(raw)
                self.export.write_text(json.dumps(actual))
                self.rebind('analysis', self.analysis)
                self.rebind('export', self.export)
                _, _, verified = input_manifest(self.path)
                self.assertEqual(verified['mapping'], original['mapping'])
                self.assertEqual(verified['l1'], original['l1'])

    def mastering_control(self, change_encoding=False):
        # Declaration-validation controls ONLY, never authentic fidelity inputs.
        rgbw = [0.64, 0.33, 0.30, 0.60, 0.15, 0.06, 0.3127, 0.3290]
        root = ET.fromstring(self.analysis.read_bytes())
        track = self.find(root, 'Outputs/Output/Video/Track')
        nodes = [self.find(track, 'PluginNode/DVGlobalData/MasteringDisplay')]
        if change_encoding:
            nodes.append(self.find(track, 'ColorEncoding'))
        for node in nodes:
            for index, name in enumerate(('Red', 'Green', 'Blue')):
                self.find(node, 'Primaries/' + name).text = ' '.join(map(str, rgbw[2*index:2*index+2]))
            self.find(node, 'WhitePoint').text = ' '.join(map(str, rgbw[6:]))
        for shot in track.findall('{' + NAMESPACE + '}Shot'):
            self.find(shot, 'PluginNode/DVDynamicData/Level9/SourceColorPrimary').text = ' '.join(map(str, rgbw))
        obj = copy.deepcopy(self.obj)
        obj['source']['mastering']['primaries'] = rgbw
        sequence = json.loads(self.sequence.read_bytes())
        sequence['source'] = copy.deepcopy(obj['source'])
        return ET.tostring(root), obj, json.dumps(sequence).encode()

    def test_non_bt2020_encoding_rejected_with_matching_mastering_l9(self):
        raw, obj, sequence = self.mastering_control(change_encoding=True)
        self.parser_rejects(raw, 'XML/source BT2020 encoding primaries mismatch', obj, sequence)

    def test_bt2020_encoding_independent_of_mastering_l9(self):
        original = self.parse_control(self.analysis.read_bytes())
        raw, obj, sequence = self.mastering_control()
        actual = self.parse_control(raw, obj, sequence)
        self.assertEqual(obj['source']['primaries'], 'bt2020')
        self.assertNotEqual(obj['source']['mastering'], self.obj['source']['mastering'])
        self.assertEqual(actual['l1'], original['l1'])
        self.assertEqual(actual['mapping'], original['mapping'])
        # Same control XML with stale mastering declaration must fail separately.
        self.parser_rejects(raw, 'actual XML mastering declaration required')

    def test_dtd_and_entities_rejected_before_parse(self):
        body = ET.tostring(ET.fromstring(self.analysis.read_bytes())).decode('utf-8')
        declarations = ['<!DOCTYPE DolbyLabsMDF>', '<!ENTITY probe "4.0.2">',
                        '<!DOCTYPE DolbyLabsMDF [<!ENTITY probe "4.0.2">]>']
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                document = declaration + body.replace('>4.0.2<', '>&probe;<')
                self.parser_rejects(document.encode('utf-8'), 'XML declarations/entities unsupported')
                for encoding, bom in [('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff')]:
                    for prefix in (b'', bom):
                        with self.subTest(encoding=encoding, bom=bool(prefix)):
                            raw = prefix + ('<?xml version="1.0" encoding="UTF-16"?>' + document).encode(encoding)
                            self.parser_rejects(raw, 'official XML requires strict UTF8 encoding')

    def test_non_utf8_xml_rejected_without_declarations(self):
        body = ET.tostring(ET.fromstring(self.analysis.read_bytes())).decode('utf-8')
        for encoding in ('utf-16-le', 'utf-16-be'):
            self.parser_rejects(body.encode(encoding), 'official XML requires strict UTF8 encoding')
        self.parser_rejects(b'<?xml version="1.0" encoding="UTF-16"?>' + body.encode(),
                            'official XML requires strict UTF8 encoding')
        self.parser_rejects(body.encode() + b'\xff', 'official XML requires strict UTF8 encoding')

    def test_missing_malformed_and_zero_l1_controls(self):
        # Deliberately altered raw XML is a parser/control test only; it is not
        # exported as an official reference or passed to a native fidelity run.
        obj, _, _ = input_manifest(self.path)
        original = self.analysis.read_bytes()
        for text_value, diagnostic in [('0 0', 'XML numeric field shape mismatch'),
                                       ('0 nan 1', 'number outside finite supported domain'),
                                       ('0 1 0', 'unordered normalized XML L1'), ('0 0 0', None)]:
            root = ET.fromstring(original)
            shot = self.find(root, 'Outputs/Output/Video/Track/Shot')
            frame = shot.findall('{' + NAMESPACE + '}Frame')[1]
            self.find(frame, 'PluginNode/DVDynamicData/Level1/ImageCharacter').text = text_value
            raw = ET.tostring(root)
            if text_value == '0 0 0':
                data = parsed_export(raw, self.sequence, self.sequence.read_bytes(), obj)
                self.assertEqual(data['l1'], {'min_pq': 0, 'avg_pq': 0, 'max_pq': 0})
            else:
                with self.assertRaisesRegex(ValueError, diagnostic):
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
            self.assertGreater(semantics['cie_y_l1']['native_' + key], 0)
            self.assertEqual(semantics['cie_y_l1']['native_' + key], struct.unpack('<f', struct.pack('<f', meta[key]))[0])
        reference = self.root / 'panel616/reference-1.json'
        official, _ = result_manifest(reference)
        self.assertEqual(official['alignment'], obj['alignment'])
        self.assertEqual(official['encoding'], obj['encoding'])
        # No numerical baseline here: deliberately mismatch before comparison.
        official['alignment']['mapping']['shot_id'] += '-wrong'
        reference.write_text(json.dumps(official))
        with self.assertRaisesRegex(ValueError, 'source/metadata/target/frame alignment mismatch'):
            compare(result, reference)

    def test_result_schema_stage_encoding_and_mapping_mixing(self):
        path = self.root / 'panel616/reference-1.json'
        original = json.loads(path.read_bytes())
        mutations = [(lambda x: x.update(schema=1), 'missing or unknown contract fields'),
                     (lambda x: x['alignment'].update(stage='consumer-rpu'), 'invalid post-reshape alignment stage/source'),
                     (lambda x: x['encoding'].update(primaries='p3'), 'reference/candidate encoding mismatch'),
                     (lambda x: x['alignment']['mapping'].update(edit_offset=3), 'post-reshape shot/frame/PTS mismatch'),
                     (lambda x: x['alignment'].update(rpu_sha256='0'*64), 'missing or unknown contract fields'),
                     (lambda x: x['alignment']['mapping']['edit_rate'].update(num=True), 'integer outside supported domain')]
        for mutate, diagnostic in mutations:
            obj = copy.deepcopy(original)
            mutate(obj)
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, diagnostic):
                result_manifest(path)


if __name__ == '__main__':
    unittest.main()
