"""Bounded official XML L1 translation; no RPU, statistics or trims generated."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from tools.dolby_harness.contracts import (bound_file, integer, keys, number,
                                         parse_json, pixels, text)

NAMESPACE = 'http://www.dolby.com/schemas/dvmd/4_0_2'
TRANSLATION = 'dolby-xml-l1-direct-v1'
PARSER_NAME = 'dolby-harness-cm4-frame-l1'
PARSER_VERSION = '1'


def parser_identity():
    return {'name': PARSER_NAME, 'version': PARSER_VERSION,
            'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def snapshot(base, binding):
    path = bound_file(base, binding)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('post-reshape artifact changed while loading')
    return path, raw


def source_sequence(path, raw, obj):
    """Verify retained sequence bytes; execution provenance is still attestation."""
    data = parse_json(raw)
    keys(data, 'schema source width height edit_rate frames provenance')
    if type(data['schema']) is not int or data['schema'] != 2:
        raise ValueError('unknown source sequence schema')
    f = obj['frame']
    if (data['source'] != obj['source'] or data['width'] != f['width'] or
            data['height'] != f['height']):
        raise ValueError('analyzed source interpretation mismatch')
    integer(data['width'], 1, 3840)
    integer(data['height'], 1, 2160)
    keys(data['edit_rate'], 'num den')
    integer(data['edit_rate']['num'], 1)
    integer(data['edit_rate']['den'], 1)
    if not isinstance(data['provenance'], dict) or not data['provenance']:
        raise ValueError('source analysis/conversion provenance required')
    if not isinstance(data['frames'], list) or not data['frames']:
        raise ValueError('whole analyzed sequence required')
    for index, frame in enumerate(data['frames']):
        keys(frame, 'index original normalized')
        if integer(frame['index']) != index:
            raise ValueError('only contiguous zero-origin sequence supported')
        bound_file(path.parent, frame['original'])
        normalized = bound_file(path.parent, frame['normalized'])
        pixels(normalized, data['width'], data['height'], frame['normalized']['sha256'])
    if f['index'] >= len(data['frames']) or data['frames'][f['index']]['normalized']['sha256'] != f['input']['sha256']:
        raise ValueError('frame not bound to analyzed sequence')
    return data


def children(node, name):
    return node.findall('{' + NAMESPACE + '}' + name)


def one(node, name):
    found = children(node, name)
    if len(found) != 1:
        raise ValueError('missing or ambiguous XML ' + name)
    return found[0]


def value(node, name):
    return text(one(node, name).text)


def xml_integer(node, name, low=0):
    token = value(node, name)
    if not token.isascii() or not token.isdecimal():
        raise ValueError('nonnegative XML integer required')
    return integer(int(token), low)


def decimals(value, count):
    tokens = value.split()
    if len(tokens) != count:
        raise ValueError('XML numeric field shape mismatch')
    return [number(float(x), 0, 1) for x in tokens]


def xml_primaries(node):
    primary = one(node, 'Primaries')
    return [x for name in ('Red', 'Green', 'Blue')
            for x in decimals(value(primary, name), 2)] + decimals(value(node, 'WhitePoint'), 2)


def selected_l1(raw, obj, sequence):
    # ElementTree does not fetch external entities; reject declarations as well.
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise ValueError('XML declarations/entities unsupported')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError('malformed official XML') from exc
    if root.tag != '{' + NAMESPACE + '}DolbyLabsMDF' or value(root, 'Version') != '4.0.2':
        raise ValueError('only CM4 XML4.0.2 supported')
    output = one(one(root, 'Outputs'), 'Output')
    if xml_integer(output, 'NumberVideoTracks', 1) != 1:
        raise ValueError('multi-track composition unsupported')
    track = one(one(output, 'Video'), 'Track')
    rates = value(track, 'EditRate').split()
    if len(rates) != 2 or any(not x.isascii() or not x.isdecimal() for x in rates):
        raise ValueError('invalid XML edit rate')
    rate = dict(zip(('num', 'den'), [integer(int(x), 1) for x in rates]))
    if rate != sequence['edit_rate']:
        raise ValueError('analysis/sequence edit rate mismatch')
    f = obj['frame']
    if f['pts']['num'] * rate['num'] != f['index'] * rate['den'] * f['pts']['den']:
        raise ValueError('frame PTS does not match zero-origin XML timeline')
    encoding = one(track, 'ColorEncoding')
    if (value(encoding, 'Encoding'), value(encoding, 'ColorSpace'), value(encoding, 'SignalRange')) != ('pq', 'rgb', 'computer'):
        raise ValueError('XML/source encoding mismatch')
    if xml_primaries(encoding) != obj['source']['mastering']['primaries']:
        raise ValueError('XML/source primaries mismatch')
    global_node = one(track, 'PluginNode')
    if value(one(global_node, 'Level254'), 'CMVersion').split() != ['4', '1']:
        raise ValueError('unsupported CM4 analysis/compatibility version')
    mastering = one(one(global_node, 'DVGlobalData'), 'MasteringDisplay')
    declared = obj['source']['mastering']
    if (xml_primaries(mastering) != declared['primaries'] or
            float(value(mastering, 'PeakBrightness')) != declared['max_nits'] or
            float(value(mastering, 'MinimumBrightness')) != declared['min_nits']):
        raise ValueError('actual XML mastering declaration required')
    shots = children(track, 'Shot')
    if not shots:
        raise ValueError('XML shots absent')
    selected = []
    previous_end = 0
    ids = set()
    for shot in shots:
        record = one(shot, 'Record')
        start, duration = xml_integer(record, 'In'), xml_integer(record, 'Duration', 1)
        sid = value(shot, 'UniqueID')
        if start != previous_end or sid in ids:
            raise ValueError('ambiguous, overlapping, rebased or sparse XML shots')
        ids.add(sid)
        previous_end = start + duration
        frames = children(shot, 'Frame')
        offsets = set()
        for frame in frames:
            offset = xml_integer(frame, 'EditOffset')
            if offset >= duration or offset in offsets:
                raise ValueError('duplicate or out-of-shot XML frame')
            offsets.add(offset)
            if start + offset == f['index']:
                dynamic = one(one(frame, 'PluginNode'), 'DVDynamicData')
                l1 = one(dynamic, 'Level1')
                if l1.get('level') != '1':
                    raise ValueError('wrong XML L1 level')
                lo, avg, hi = decimals(value(l1, 'ImageCharacter'), 3)
                if not lo <= avg <= hi:
                    raise ValueError('unordered normalized XML L1')
                # L9 is a declaration, not dynamic processing applied here.
                shot_dynamic = one(one(shot, 'PluginNode'), 'DVDynamicData')
                l9 = one(shot_dynamic, 'Level9')
                if (value(l9, 'SourceColorModel') != '255' or
                        decimals(value(l9, 'SourceColorPrimary'), 8) != declared['primaries']):
                    raise ValueError('applicable L9/source declaration mismatch')
                selected.append(({'track_id': value(track, 'UniqueID'), 'shot_id': sid,
                                  'shot_in': start, 'shot_duration': duration,
                                  'edit_offset': offset, 'edit_rate': rate},
                                 {'min_pq': lo, 'avg_pq': avg, 'max_pq': hi}))
    if previous_end != len(sequence['frames']) or len(selected) != 1:
        raise ValueError('missing or ambiguous frame-local XML L1 mapping')
    return selected[0]


def parsed_export(analysis_raw, sequence_path, sequence_raw, obj):
    sequence = source_sequence(sequence_path, sequence_raw, obj)
    mapping, l1 = selected_l1(analysis_raw, obj, sequence)
    return {'schema': 2, 'stage': 'post-reshape',
            'analysis_sha256': hashlib.sha256(analysis_raw).hexdigest(),
            'source_manifest_sha256': hashlib.sha256(sequence_raw).hexdigest(),
            'source_sha256': obj['frame']['input']['sha256'],
            'frame_index': obj['frame']['index'], 'pts': obj['frame']['pts'],
            'parser': parser_identity(), 'xml_version': '4.0.2', 'analysis_version': 4,
            'mapping': mapping, 'l1': l1, 'translation': TRANSLATION}


def metadata(base, envelope, obj):
    keys(envelope, 'origin analysis export source_manifest frame_index pts')
    f = obj['frame']
    integer(envelope['frame_index'])
    keys(envelope['pts'], 'num den')
    integer(envelope['pts']['num'], -2**53 + 1)
    integer(envelope['pts']['den'], 1)
    if envelope['origin'] != 'dolby-tools' or envelope['frame_index'] != f['index'] or envelope['pts'] != f['pts']:
        raise ValueError('official metadata/frame identity required')
    _, analysis = snapshot(base, envelope['analysis'])
    source_path, source = snapshot(base, envelope['source_manifest'])
    _, export = snapshot(base, envelope['export'])
    data = parse_json(export)
    expected = parsed_export(analysis, source_path, source, obj)
    keys(data, 'schema stage analysis_sha256 source_manifest_sha256 source_sha256 frame_index pts parser xml_version analysis_version mapping l1 translation')
    # JSON equality alone accepts bool == int; enforce numeric domains explicitly.
    if type(data['schema']) is not int or type(data['analysis_version']) is not int:
        raise ValueError('integer export schema/version required')
    integer(data['frame_index'])
    keys(data['pts'], 'num den')
    integer(data['pts']['num'], -2**53 + 1)
    integer(data['pts']['den'], 1)
    keys(data['mapping'], 'track_id shot_id shot_in shot_duration edit_offset edit_rate')
    for k in ('shot_in', 'shot_duration', 'edit_offset'):
        integer(data['mapping'][k], 1 if k == 'shot_duration' else 0)
    keys(data['mapping']['edit_rate'], 'num den')
    for k in ('num', 'den'):
        integer(data['mapping']['edit_rate'][k], 1)
    keys(data['l1'], 'min_pq avg_pq max_pq')
    for x in data['l1'].values():
        number(x, 0, 1)
    if data != expected:
        raise ValueError('export differs from bound official XML/parser/sequence')
    return {**data, 'max_pq_y': data['l1']['max_pq'], 'avg_pq_y': data['l1']['avg_pq']}
