"""Deferred authored adapter regressions. No vendor execution or fake DV XML.

Public controls are metadata-free storage/transport or rejection-only malformed
XML. Positive metadata comes only from HDR_AUTHORED_INPUT's retained real XML.
Run once only after complete adapter review/fixes. Native tests reject controls
before Vulkan; the one genuine candidate render belongs to recovery validation.
"""
import copy
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
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import authored_master as master
from tools.dolby_harness.contracts import ENCODING, alignment, input_manifest, result_manifest
from tools.dolby_harness.harness import baseline_semantics, control
from tools.dolby_harness.master_pixels import decode, geometry, header, normalize, sha, verify
from tools.dolby_harness.provenance import FRONTEND_INPUTS, ROOT, implementation


def exr(width, height, samples, compression=0):
    """Public metadata-free HALF storage fixture, not Dolby tool input/output."""
    def attr(name, typ, data):
        return name.encode() + b'\0' + typ.encode() + b'\0' + struct.pack('<I', len(data)) + data
    channels = b''.join(c.encode() + b'\0' + struct.pack('<iB3xii', 1, 0, 1, 1) for c in ('B', 'G', 'R')) + b'\0'
    box = struct.pack('<4i', 0, 0, width - 1, height - 1)
    hdr = struct.pack('<II', 20000630, 2) + attr('channels', 'chlist', channels)
    hdr += attr('compression', 'compression', bytes([compression]))
    hdr += attr('dataWindow', 'box2i', box) + attr('displayWindow', 'box2i', box)
    hdr += attr('lineOrder', 'lineOrder', b'\0') + attr('pixelAspectRatio', 'float', struct.pack('<f', 1)) + b'\0'
    rows = 16 if compression == 3 else 1
    chunks = []
    for y in range(0, height, rows):
        raw = b''.join(struct.pack('<e', samples[row * width + x][c])
                       for row in range(y, min(y + rows, height)) for c in (2, 1, 0) for x in range(width))
        packed = raw
        if compression == 3:
            separated = raw[::2] + raw[1::2]
            predicted = bytes([separated[0]]) + bytes((separated[i] - separated[i - 1] + 128) & 255 for i in range(1, len(separated)))
            zipped = zlib.compress(predicted)
            if len(zipped) < len(raw):
                packed = zipped
        chunks.append(struct.pack('<iI', y, len(packed)) + packed)
    offset = len(hdr) + len(chunks) * 8
    table = b''
    for chunk in chunks:
        table += struct.pack('<Q', offset)
        offset += len(chunk)
    return hdr + table + b''.join(chunks)


def public_transport():
    return {'schema': 3, 'stage': master.STAGE,
            'frame': {'width': 4096, 'height': 1},
            'source': {'system': 'rgb', 'transfer': 'pq', 'primaries': 'p3d65', 'range': 'full',
                       'sample_format': 'ieee754-binary16-expanded-f32', 'layout': 'c3-f32le', 'orientation': 'top-left',
                       'mastering': {'min_nits': 0.005, 'max_nits': 4000, 'primaries': master.P3}},
            'target': {'id': 'public-transport-physical-target', 'min_nits': 0, 'max_nits': 600, 'primaries': master.P3}}


class StorageTransportTests(unittest.TestCase):
    def test_half_exact_channels_rows_no_integer_or_gamma_transform(self):
        samples = [(0, 0.5, 1), (0.25, 0.0625, 0.75), (2**-24, 0.03125, 0.125), (1, 0.0, 0.5)]
        raw = exr(2, 2, samples)
        h, got = decode(raw)
        expected = b''.join(struct.pack('<3f', *x) for x in samples)
        self.assertEqual(got, expected)
        self.assertEqual(h['channels'], ['B', 'G', 'R'])
        verify(raw, expected, 2, 2)
        for replacement in (bytes(reversed(expected)), b''.join(struct.pack('<f', x / 65535) for p in samples for x in p)):
            with self.assertRaisesRegex(ValueError, 'exact sample'):
                verify(raw, replacement, 2, 2)

    def test_zip_and_verbatim_storage(self):
        samples = [(0.125, 0.25, 0.5)] * (17 * 7)
        uncompressed = decode(exr(7, 17, samples))[1]
        self.assertEqual(decode(exr(7, 17, samples, 3))[1], uncompressed)
        self.assertEqual(decode(exr(1, 1, [(0.25, 0.5, 1)], 3))[1], struct.pack('<3f', 0.25, 0.5, 1))

    def test_half_finite_domain_and_tamper_rejection(self):
        for x in (math.nan, math.inf, -0.01, 1.1):
            with self.subTest(x=x), self.assertRaisesRegex(ValueError, 'finite normalized HALF'):
                decode(exr(1, 1, [(x, 0, 0)]))
        raw = exr(1, 1, [(0.125, 0.25, 0.5)])
        for bad in (raw[:-1], raw + b'\0', raw[:4] + struct.pack('<I', 0x202) + raw[8:]):
            with self.assertRaises(ValueError):
                decode(bad)
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'fixture.exr'
                path.write_bytes(raw)
                normalize(path, Path(directory) / 'output', '0' * 64)

    def test_geometry_and_schema_separation(self):
        self.assertEqual(geometry(4096, 2160), 4096 * 2160)
        for w, h in ((4097, 1), (1, 2161), (0, 1), (True, 1)):
            with self.assertRaises(ValueError):
                geometry(w, h)
        self.assertEqual(header(exr(4096, 1, [(0, 0, 0)] * 4096))['width'], 4096)
        # No old schema's geometry or source interpretation is relaxed.
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'input.json'
            for schema in (1, 2):
                obj = public_transport()
                obj['schema'] = schema
                obj['frame'].update(index=0, pts={'num': 0, 'den': 1}, content_id='public', input={'file': 'absent', 'sha256': '0' * 64})
                obj['metadata'] = None
                if schema == 1:
                    del obj['stage']
                else:
                    obj['stage'] = 'post-reshape'
                p.write_text(json.dumps(obj))
                with self.assertRaisesRegex(ValueError, 'integer outside'):
                    input_manifest(p)

    def test_dvh2_metadata_free_transport_and_physical_encoding_separation(self):
        obj = public_transport()
        # Zero baseline slots, not an invented Dolby record or fidelity input.
        tokens = control(obj, {'max_pq_y': 0, 'avg_pq_y': 0}).split()
        self.assertEqual(tokens[:4], ['DVH2', '4096', '1', '1'])
        self.assertEqual(len(tokens), 26)
        self.assertEqual(tokens[-2:], ['0', '0'])
        self.assertNotIn('bit_depth', obj['source'])
        self.assertEqual(ENCODING['primaries'], 'bt2020')
        self.assertEqual(obj['source']['primaries'], 'p3d65')
        self.assertEqual(obj['target']['primaries'], master.P3)
        for field, value in (('sample_format', 'uint16'), ('transfer', 'linear'), ('primaries', 'bt2020')):
            bad = copy.deepcopy(obj)
            bad['source'][field] = value
            with self.assertRaisesRegex(ValueError, 'unsupported authored'):
                master.source_target(bad['source'], bad['target'])

    def test_native_dvh2_rejections_before_vulkan(self):
        native = os.environ.get('HDR_HARNESS_NATIVE')
        self.assertIsNotNone(native, 'reviewed batch requires compiled native consumer')
        assert native is not None
        tokens = control(public_transport(), {'max_pq_y': 0, 'avg_pq_y': 0}).split()
        controls = ['DVH2', 'DVH2 4097 1 1', 'DVH2 1 2161 1', 'DVH2 1 1 0',
                    'DVH2 1 1 2', ' '.join(tokens + ['trailing']), ' '.join(tokens[:-1]),
                    'DVH1 4096 1 0 0 10']
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            for i, data in enumerate(controls):
                source, output = p / ('control' + str(i)), p / ('out' + str(i))
                source.write_text(data + '\n')
                run = subprocess.run([native, str(source), str(p / 'absent'), str(output)], capture_output=True, timeout=20)
                self.assertEqual(run.returncode, 2)
                self.assertIn(b'Invalid native control protocol', run.stderr)
                self.assertFalse(output.exists())
                self.assertNotIn(b'libplacebo=', run.stdout)

    def test_xml_security_and_strict_json_types(self):
        for raw in (b'<!DOCTYPE x><x/>', b'<!ENTITY x "y"><x/>', b'\xff', '<x/>'.encode('utf16'), b'<x/>'):
            with self.assertRaises(ValueError):
                master.document(raw)
        self.assertFalse(master.strict_equal([0, 0], [False, 0]))
        self.assertFalse(master.strict_equal({'x': 1}, {'x': 1.0}))
        self.assertIn('tools/dolby_harness/authored_master.py', FRONTEND_INPUTS)
        self.assertIn('tools/dolby_harness/master_pixels.py', FRONTEND_INPUTS)

    def test_legacy_dvh1_control_bytes_unchanged(self):
        obj = {'schema': 1, 'frame': {'width': 2, 'height': 1},
               'source': {'system': 'rgb', 'range': 'full', 'bit_depth': 10,
                          'mastering': {'min_nits': 0, 'max_nits': 1000,
                                        'primaries': [0.708, 0.292, 0.17, 0.797, 0.131, 0.046, 0.3127, 0.329]}},
               'target': {'min_nits': 0, 'max_nits': 600, 'primaries': master.P3}}
        expected = ('DVH1 2 1 0 0 10 0 1000 0.708 0.292 0.17 0.797 0.131 0.046 0.3127 0.329 '
                    '0 600 0.68 0.32 0.265 0.69 0.15 0.06 0.3127 0.329 0 0\n')
        self.assertEqual(control(obj, None), expected)
        obj.update(schema=2, stage='post-reshape')
        self.assertEqual(control(obj, None), expected)

    def test_new_frontend_sources_and_artifact_hash_tamper(self):
        read_bytes = Path.read_bytes
        for source in ('authored_master.py', 'master_pixels.py'):
            target = ROOT / 'tools/dolby_harness' / source
            def changed(path):
                return read_bytes(path) + (b'\n# changed\n' if path == target else b'')
            with patch.object(Path, 'read_bytes', changed):
                with self.assertRaisesRegex(ValueError, 'changed since import'):
                    implementation()
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'artifact'
            p.write_bytes(b'public metadata-free transport bytes')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                master.snapshot(directory, {'file': str(p), 'sha256': '0' * 64})


class GenuineAuthoredTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get('HDR_AUTHORED_INPUT')
        if not source:
            raise AssertionError('real private HDR_AUTHORED_INPUT required; no fake/skip replacement')
        cls.path = Path(source)
        cls.obj, _, cls.meta = input_manifest(cls.path)
        cls.base = cls.path.parent
        e = cls.obj['metadata']
        cls.actual = master.snapshot(cls.base, e['analysis'])[1]
        cls.original = master.snapshot(cls.base, e['original_analysis'])[1]
        cls.repair = master.snapshot(cls.base, e['declaration_repair'])[1]
        cls.sequence_path, cls.sequence_raw = master.snapshot(cls.base, e['source_manifest'])
        cls.sequence = json.loads(cls.sequence_raw)

    def selected(self, root=None, obj=None, sequence=None):
        return master.selected_metadata(root if root is not None else master.document(self.actual),
                                        obj if obj is not None else self.obj,
                                        sequence if sequence is not None else self.sequence)

    def test_actual_selected_mapping_rate_and_sparse_acquisition(self):
        mapping, l1, records = self.selected()
        self.assertEqual(mapping, self.meta['mapping'])
        self.assertEqual(l1, self.meta['l1'])
        self.assertEqual(records, self.meta['records'])
        self.assertEqual(mapping['shot_in'] + mapping['edit_offset'], self.obj['frame']['index'])
        self.assertEqual([f['index'] for f in self.sequence['frames']], [0])
        self.assertGreater(mapping['shot_duration'], len(self.sequence['frames']))
        self.assertEqual(mapping['edit_rate'], {'num': 60000, 'den': 1001})

    def test_original_repair_rollback_exact_and_only_two_insertions(self):
        master.repaired(self.original, self.actual, self.repair)
        for name, raw in (('actual', self.actual.replace(b'<PeakBrightness>600</PeakBrightness>', b'<PeakBrightness>601</PeakBrightness>', 1)),
                          ('original', self.original + b'\n')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                master.repaired(raw if name == 'original' else self.original, raw if name == 'actual' else self.actual, self.repair)
        r = json.loads(self.repair)
        r['repair_insertion']['algorithm_insertion']['offset'] += 1
        with self.assertRaisesRegex(ValueError, 'insertion bytes/hash'):
            master.repaired(self.original, self.actual, json.dumps(r).encode())

    def test_l2_verbatim_unapplied_and_no_named_cm_or_cie_y_claim(self):
        root = master.document(self.actual)
        shot = master.track(root)[1].find('Shot')
        actual = [(e.findtext('TID'), e.findtext('Trim'), list(map(list, e.attrib.items()))) for e in shot.find('PluginNode') if e.get('level') == '2']
        retained = [(str(r['target_id']), r['fields'][1]['text'], r['attributes']) for r in self.meta['records'] if r['level'] == 2 and r['scope'] == 'shot']
        self.assertEqual(actual, retained)
        self.assertTrue(all(r['operator'] == 'not-implemented' for r in self.meta['records'] if r['level'] == 2))
        semantics = baseline_semantics(self.obj, self.meta)
        self.assertNotIn('cie_y_l1', semantics)
        self.assertIsNone(self.meta['selected_cm_name'])
        self.assertEqual(self.meta['algorithm_versions'], [0, 0])
        self.assertEqual(semantics['trims'], 'not implemented')
        self.assertIn('no integer divisor', semantics['range']['samples'])
        self.assertEqual(control(self.obj, self.meta).split()[-2:], [str(self.meta['l1']['max_pq']), str(self.meta['l1']['avg_pq'])])

    def test_parser_ambiguity_rejections_not_stale_export_guard(self):
        def duplicate_target(t):
            c = t.find('PluginNode/DolbyEDR/Characteristics')
            c.append(copy.deepcopy(c.find('TargetDisplay')))
        def duplicate_frame(t):
            s = t.find('Shot')
            s.append(copy.deepcopy(s.find('Frame')))
        def overlap(t):
            t.findall('Shot')[1].find('Record/In').text = '0'
        def duplicate_parent(root):
            s = root.find('SourceList')
            s.append(copy.deepcopy(s.find('Source')))
        cases = [(lambda r: duplicate_target(master.track(r)[1]), 'ambiguous authored target'),
                 (lambda r: duplicate_frame(master.track(r)[1]), 'duplicate/out-of-shot'),
                 (lambda r: overlap(master.track(r)[1]), 'overlapping authored shot'),
                 (duplicate_parent, 'ambiguous authored source'),
                 (lambda r: r.find('Outputs').append(copy.deepcopy(r.find('Outputs/Output'))), 'ambiguous authored XML Output')]
        for mutate, error in cases:
            root = master.document(self.actual)
            mutate(root)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.selected(root=root)

    def test_selected_l1_missing_conflicting_and_target_source_rejections(self):
        for mutate, error in (
                (lambda t: t.find('Shot/Frame/PluginNode').clear(), 'explicit selected frame-local'),
                (lambda t: setattr(t.find('Shot/Frame/PluginNode/DolbyEDR/ImageCharacter'), 'text', '0,0.1,0.2'), 'conflicting selected'),
                (lambda t: setattr(t.find('Shot/Source/ParentID'), 'text', 'absent-parent'), 'ParentID missing'),
                (lambda t: setattr(t.find('Shot/Frame/EditOffset'), 'text', '512'), 'duplicate/out-of-shot')):
            root = master.document(self.actual)
            mutate(master.track(root)[1])
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.selected(root=root)
        for key in ('source', 'target'):
            obj = copy.deepcopy(self.obj)
            volume = obj['source']['mastering'] if key == 'source' else obj['target']
            volume['max_nits'] += 1
            with self.assertRaisesRegex(ValueError, 'mastering mismatch|physical target tuple'):
                self.selected(obj=obj)
        obj = copy.deepcopy(self.obj)
        obj['frame']['pts']['num'] += 1
        with self.assertRaisesRegex(ValueError, 'frame/PTS/rate'):
            self.selected(obj=obj)

    def test_export_and_alignment_strict_tamper_rejection(self):
        aligned = alignment(self.obj, self.meta)
        master.validate_alignment(aligned)
        for field, value in (('selected_cm_name', 'CM2.9'), ('algorithm_versions', [False, 0]), ('xml_version', '4.0.2')):
            bad = copy.deepcopy(aligned)
            bad[field] = value
            with self.assertRaisesRegex(ValueError, 'unsupported authored'):
                master.validate_alignment(bad)
        with tempfile.TemporaryDirectory() as directory:
            export = Path(directory) / 'export.json'
            e = copy.deepcopy(self.obj['metadata'])
            for key, value in (('schema', True), ('frame_index', False), ('selected_cm_name', 'CM4'), ('records', [])):
                bad = copy.deepcopy(self.meta)
                del bad['max_pq_y'], bad['avg_pq_y']
                bad[key] = value
                raw = json.dumps(bad).encode()
                export.write_bytes(raw)
                e['export'] = {'file': str(export), 'sha256': sha(raw)}
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'export differs'):
                    master.metadata(self.base, e, self.obj)

    def test_sparse_manifest_domain_rejections(self):
        for mutate, error in ((lambda d: d.update(kind='full-sequence'), 'sparse authored'),
                              (lambda d: d.update(width=4097), 'integer outside'),
                              (lambda d: d['edit_rate'].update(num=True), 'integer outside'),
                              (lambda d: d.update(frames=[]), 'bounded acquired')):
            data = copy.deepcopy(self.sequence)
            mutate(data)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                master.source_manifest(self.sequence_path, json.dumps(data).encode(), self.obj)

    def test_sparse_duplicate_and_normalized_identity_rejections(self):
        data = copy.deepcopy(self.sequence)
        data['frames'].append(copy.deepcopy(data['frames'][0]))
        data['provenance']['conversions'].append(copy.deepcopy(data['provenance']['conversions'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate sparse frame'):
            master.source_manifest(self.sequence_path, json.dumps(data).encode(), self.obj)
        data = copy.deepcopy(self.sequence)
        data['frames'][0]['normalized']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            master.source_manifest(self.sequence_path, json.dumps(data).encode(), self.obj)

    def test_retained_reference_binding_and_log_hashes_without_vendor_call(self):
        receipt = json.loads(self.repair)
        reference = {'file': receipt['Mac_reference']['path'], 'sha256': receipt['Mac_reference']['sha256']}
        provenance = master.reference_provenance(self.base, self.obj['metadata']['declaration_repair'], self.obj, self.meta, reference)
        self.assertIsNone(provenance['selected_cm_name'])
        self.assertEqual(len(provenance['logs']), 3)
        bad = copy.deepcopy(self.obj)
        bad['target']['max_nits'] = 601
        with self.assertRaisesRegex(ValueError, 'only acquired'):
            master.reference_provenance(self.base, self.obj['metadata']['declaration_repair'], bad, self.meta, reference)


if __name__ == '__main__':
    unittest.main()
