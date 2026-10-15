"""Strict XML2.0.5 authored-master baseline; authentic declarations, no trim math.

Only normalized L1 max/average enter existing baseline slots. Decimal records
are retained unapplied. No named consumer CM, RPU or photometric claim is inferred.
"""
import json
from functools import wraps
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

from tools.dolby_harness.contracts import (digest, integer, keys, luminance,
                                         number, parse_json, text)
from tools.dolby_harness.master_pixels import (geometry, read_bounded, sha,
                                              validate_decoder, verify)

STAGE = 'authored-master-baseline'
TRANSLATION = 'dolby-xml205-l1-direct-baseline-v1'
P3 = [0.68, 0.32, 0.265, 0.69, 0.15, 0.06, 0.3127, 0.329]
IDENTITIES = ('stage analysis_sha256 original_analysis_sha256 declaration_repair_sha256 '
              'source_manifest_sha256 parser xml_version algorithm_versions selected_cm_name mapping translation')
EXPORT_KEYS = ('schema ' + IDENTITIES + ' source_sha256 frame_index pts l1 records')
MAPPING_KEYS = ('output_id track_id shot_id frame_id source_parent_id source_in '
                'shot_in shot_duration edit_offset edit_rate')


def validation(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, TypeError, IndexError, OverflowError, struct.error) as exc:
            raise ValueError('malformed authored contract structure') from exc
    return checked


def parser_identity():
    return {'name': 'dolby-harness-authored-xml205', 'version': '1',
            'sha256': sha(Path(__file__).read_bytes())}


def snapshot(base, binding, maximum=4 * 1024 * 1024):
    keys(binding, 'file sha256')
    path = Path(base) / text(binding['file'])
    digest(binding['sha256'])
    raw = read_bounded(path, maximum)
    if sha(raw) != binding['sha256']:
        raise ValueError('authored artifact SHA256 mismatch')
    return path, raw


def retained(base, entry):
    # Historical receipts contain absolute paths on their recording host. A
    # durable relocation uses the exact SHA as filename, never edits the receipt
    # or asserts that a missing artifact has been verified. Main input envelopes
    # still use their declared file paths without any relocation fallback.
    path = Path(text(entry['path']))
    if not path.is_file():
        path = Path(base) / 'retained' / digest(entry['sha256'])
    return snapshot(base, {'file': str(path), 'sha256': entry['sha256']})


def strict_equal(a, b):
    # Exact JSON types as well as values: True is never an integer or 1.0.
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def source_target(source, target):
    keys(source, 'system transfer primaries range sample_format layout orientation mastering')
    if [source[k] for k in ('system', 'transfer', 'primaries', 'range', 'sample_format', 'layout', 'orientation')] != [
            'rgb', 'pq', 'p3d65', 'full', 'ieee754-binary16-expanded-f32', 'c3-f32le', 'top-left']:
        raise ValueError('unsupported authored source interpretation')
    keys(source['mastering'], 'min_nits max_nits primaries')
    luminance(source['mastering'])
    if source['mastering']['primaries'] != P3:
        raise ValueError('P3D65 authored source primaries required')
    keys(target, 'id min_nits max_nits primaries')
    text(target['id'])
    luminance(target)


def one(node, name):
    nodes = node.findall(name)
    if len(nodes) != 1:
        raise ValueError('missing or ambiguous authored XML ' + name)
    return nodes[0]


def value(node, name):
    child = one(node, name)
    if len(child):
        raise ValueError('authored XML scalar required')
    return text(child.text)


def xml_int(node, name, low=0):
    token = value(node, name)
    if not re.fullmatch(r'[0-9]+', token):
        raise ValueError('nonnegative authored XML integer required')
    return integer(int(token), low)


def rate(node):
    r = one(node, 'Rate')
    return {'num': xml_int(r, 'n', 1), 'den': xml_int(r, 'd', 1)}


def decimals(token, count, low=0.0, high=1.0):
    fields = token.split(',')
    if len(fields) != count or any(not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', x) for x in fields):
        raise ValueError('authored decimal record shape/domain mismatch')
    return [number(float(x), low, high) for x in fields]


def primaries(node):
    p = one(node, 'Primaries')
    return [x for k in ('Red', 'Green', 'Blue') for x in decimals(value(p, k), 2)] + decimals(value(node, 'WhitePoint'), 2)


def display(node):
    return {'min_nits': number(float(value(node, 'MinimumBrightness')), 0, 10000),
            'max_nits': number(float(value(node, 'PeakBrightness')), 0.000001, 10000),
            'primaries': primaries(node)}


def signal(node):
    if tuple(value(node, k) for k in ('Encoding', 'ColorSpace', 'SignalRange', 'ChromaFormat')) != ('pq', 'rgb', 'computer', '444'):
        raise ValueError('authored PQ RGB full 444 declaration required')


def document(raw):
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('authored XML resource bound exceeded')
    try:
        decoded = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('authored XML requires strict UTF8') from exc
    declaration = re.match(r'^<\?xml\s+([^?]*)\?>', decoded)
    encoding = re.search(r'\bencoding\s*=\s*([\x22\x27])(.*?)\1', declaration[1]) if declaration else None
    if '\0' in decoded or (encoding and encoding[2].lower() not in ('utf8', 'utf-8')):
        raise ValueError('authored XML requires strict UTF8')
    if '<!DOCTYPE' in decoded or '<!ENTITY' in decoded:
        raise ValueError('authored XML DTD/entities forbidden')
    try:
        root = ET.fromstring(decoded)
    except ET.ParseError as exc:
        raise ValueError('malformed authored XML') from exc
    if root.tag != 'DolbyLabsMDF' or root.get('version') != '2.0.5':
        raise ValueError('only unnamespaced DolbyLabsMDF2.0.5 supported')
    if any('{' in n.tag for n in root.iter()):
        raise ValueError('namespaced authored XML element unsupported')
    return root


def track(root):
    output = one(one(root, 'Outputs'), 'Output')
    if xml_int(output, 'NumberVideoTracks', 1) != 1:
        raise ValueError('authored multi-track output unsupported')
    return output, one(one(output, 'Video'), 'Track')


def semantic(node):
    return (node.tag, dict(node.attrib), (node.text or '').strip(), [semantic(x) for x in node])


@validation
def repaired(original_raw, analysis_raw, receipt_raw):
    receipt = parse_json(receipt_raw)
    original = document(original_raw)
    actual = document(analysis_raw)
    if receipt.get('schema') != 'hdr.sparks-source-associated-reference.v1':
        raise ValueError('verified source-associated repair receipt required')
    if (receipt['originals'][1]['sha256'] != sha(original_raw) or
            receipt['new_derivative']['sha256'] != sha(analysis_raw)):
        raise ValueError('repair original/actual XML identity mismatch')
    repair = receipt['repair_insertion']
    # Reverse in the actual order, preserving every other byte, not a reserialize.
    prior = analysis_raw
    for name in ('algorithm_insertion', 'prior_color_insertion'):
        item = repair[name]
        off = integer(item['offset'], 0, len(prior))
        size = integer(item['bytes'], 1, 4096)
        chunk = prior[off:off + size]
        if len(chunk) != size or sha(chunk) != digest(item['sha256']):
            raise ValueError('declaration insertion bytes/hash mismatch')
        if name == 'algorithm_insertion' and chunk.decode('utf8') != item['text']:
            raise ValueError('algorithm insertion text mismatch')
        prior = prior[:off] + prior[off + size:]
    if prior != original_raw:
        raise ValueError('two-insertion raw rollback does not reconstruct original XML')
    _, original_track = track(original)
    _, actual_track = track(actual)
    global_edr = one(one(actual_track, 'PluginNode'), 'DolbyEDR')
    original_edr = one(one(original_track, 'PluginNode'), 'DolbyEDR')
    if original_track.findall('ColorEncoding') or original_edr.findall('AlgorithmVersions'):
        raise ValueError('repair locations not absent in original')
    encoding = one(actual_track, 'ColorEncoding')
    algorithm = one(global_edr, 'AlgorithmVersions')
    if algorithm.attrib or list(algorithm) or algorithm.text != '0,0':
        raise ValueError('only actual source-associated AlgorithmVersions0,0 supported')
    if set(x.tag for x in encoding) != set('Primaries WhitePoint MinimumBrightness PeakBrightness Encoding ColorSpace SignalRange BitDepth ChromaFormat'.split()):
        raise ValueError('unexpected repaired ColorEncoding fields')
    signal(encoding)
    if primaries(encoding) != P3 or display(encoding) != {'min_nits': 0.0, 'max_nits': 10000.0, 'primaries': P3} or xml_int(encoding, 'BitDepth') != 16:
        raise ValueError('repaired source ColorEncoding mismatch')
    actual_track.remove(encoding)
    global_edr.remove(algorithm)
    if semantic(original) != semantic(actual):
        raise ValueError('changes beyond declared source insertions')
    return document(analysis_raw), receipt


@validation
def source_manifest(path, raw, obj):
    data = parse_json(raw)
    keys(data, 'schema kind source width height edit_rate frames provenance')
    if type(data['schema']) is not int or data['schema'] != 3 or data['kind'] != 'sparse-authored-master':
        raise ValueError('sparse authored source manifest3 required')
    geometry(data['width'], data['height'])
    f = obj['frame']
    if not strict_equal(data['source'], obj['source']) or (data['width'], data['height']) != (f['width'], f['height']):
        raise ValueError('sparse source declarations mismatch')
    keys(data['edit_rate'], 'num den')
    for k in ('num', 'den'):
        integer(data['edit_rate'][k], 1)
    provenance = data['provenance']
    keys(provenance, 'publication acquisition conversions authority')
    text(provenance['authority'])  # Explicit retained association, not hash authentication.
    snapshot(path.parent, provenance['publication'])
    snapshot(path.parent, provenance['acquisition'])
    if not isinstance(data['frames'], list) or not 1 <= len(data['frames']) <= 64:
        raise ValueError('bounded acquired sparse frame list required')
    conversions = provenance['conversions']
    if not isinstance(conversions, list) or len(conversions) != len(data['frames']):
        raise ValueError('one storage conversion receipt per acquired frame required')
    seen, selected = set(), None
    for frame, conversion in zip(data['frames'], conversions):
        keys(frame, 'index original normalized')
        index = integer(frame['index'])
        if index in seen:
            raise ValueError('duplicate sparse frame index')
        seen.add(index)
        _, original = snapshot(path.parent, frame['original'], 256 * 1024 * 1024)
        _, normalized = snapshot(path.parent, frame['normalized'], geometry(data['width'], data['height']) * 12)
        header = verify(original, normalized, data['width'], data['height'])
        fps = header['attributes'].get('framesPerSecond')
        if fps is not None:
            n, d = struct.unpack('<iI', bytes.fromhex(fps['hex']))
            if fps['type'] != 'rational' or {'num': n, 'den': d} != data['edit_rate']:
                raise ValueError('original EXR/sparse edit rate mismatch')
        timecode = header['attributes'].get('timeCode')
        if index == 0 and timecode is not None and (timecode['type'] != 'timecode' or
                struct.unpack('<II', bytes.fromhex(timecode['hex']))[0] != 0):
            raise ValueError('original frame0 EXR timecode mismatch')
        _, conversion_raw = snapshot(path.parent, conversion)
        converted = parse_json(conversion_raw)
        validate_decoder(converted['decoder'])
        if (type(converted.get('schema')) is not int or converted['schema'] != 3 or
                converted.get('operation') != 'HALF-exact-binary32-storage-only' or
                converted.get('transforms') != [] or
                converted['original']['sha256'] != frame['original']['sha256'] or
                converted['normalized']['sha256'] != frame['normalized']['sha256'] or
                converted.get('header') != header or
                (converted.get('width'), converted.get('height')) != (data['width'], data['height']) or
                converted.get('entry_point') != 'tools.dolby_harness.master_pixels.normalize' or
                not isinstance(converted.get('argv'), list) or not converted['argv'] or
                not all(isinstance(x, str) and x for x in converted['argv'])):
            raise ValueError('storage conversion provenance mismatch')
        if index == f['index']:
            if frame['normalized']['sha256'] != f['input']['sha256']:
                raise ValueError('selected sparse normalized frame mismatch')
            selected = frame
    if selected is None:
        raise ValueError('selected frame not acquired in sparse manifest')
    return data, selected


def records(node, scope, targets):
    plugin = one(node, 'PluginNode')
    result, seen = [], set()
    for edr in plugin:
        if edr.tag != 'DolbyEDR' or edr.get('level') not in ('1', '2'):
            raise ValueError('unsupported authored dynamic record')
        level = int(edr.get('level'))
        tid = xml_int(edr, 'TID') if level == 2 else None
        if tid is not None and str(tid) not in targets:
            raise ValueError('authored trim target not declared')
        if (level, tid) in seen:
            raise ValueError('duplicate authored dynamic level/target')
        seen.add((level, tid))
        allowed = ['ImageCharacter'] if level == 1 else ['TID', 'Trim']
        if [x.tag for x in edr] != allowed:
            raise ValueError('unsupported authored record field/order')
        if level == 1:
            lo, avg, hi = decimals(value(edr, 'ImageCharacter'), 3)
            if not lo <= avg <= hi:
                raise ValueError('unordered normalized authored L1')
        else:
            decimals(value(edr, 'Trim'), 9, -1e6, 1e6)
        result.append({'level': level, 'scope': scope, 'target_id': tid,
                       'attributes': list(map(list, edr.attrib.items())),
                       'fields': [{'name': x.tag, 'text': x.text,
                                   'attributes': list(map(list, x.attrib.items()))} for x in edr],
                       'operator': 'not-implemented' if level == 2 else 'direct-baseline-slots'})
    return result


@validation
def selected_metadata(root, obj, sequence):
    output, t = track(root)
    edit_rate = rate(t)
    if edit_rate != sequence['edit_rate']:
        raise ValueError('authored XML/sparse edit rate mismatch')
    f = obj['frame']
    if f['pts']['num'] * edit_rate['num'] != f['index'] * edit_rate['den'] * f['pts']['den']:
        raise ValueError('authored frame/PTS/rate mismatch')
    encoding = one(t, 'ColorEncoding')
    signal(encoding)
    if primaries(encoding) != P3:
        raise ValueError('authored source encoding primaries mismatch')
    edr = one(one(t, 'PluginNode'), 'DolbyEDR')
    if value(edr, 'AlgorithmVersions') != '0,0':
        raise ValueError('unsupported authored algorithm versions')
    characteristics = one(edr, 'Characteristics')
    mastering = one(characteristics, 'MasteringDisplay')
    signal(mastering)
    if display(mastering) != obj['source']['mastering']:
        raise ValueError('authored source mastering mismatch')
    targets = {}
    for target in characteristics.findall('TargetDisplay'):
        tid = str(xml_int(target, 'ID'))
        if tid in targets:
            raise ValueError('ambiguous authored target ID')
        targets[tid] = target
    target_id = obj['target']['id']
    if target_id not in targets:
        raise ValueError('selected authored target absent')
    target = targets[target_id]
    signal(target)
    if display(target) != {k: v for k, v in obj['target'].items() if k != 'id'}:
        raise ValueError('authored physical target tuple mismatch')
    sources = {}
    for source in one(root, 'SourceList').findall('Source'):
        uid = value(source, 'UniqueID')
        if uid in sources or source.get('type') != 'Video':
            raise ValueError('ambiguous authored source ParentID')
        sources[uid] = source
    selected, ids, frame_ids, end = [], set(), set(), 0
    shots = t.findall('Shot')
    if not shots:
        raise ValueError('authored shots absent')
    for shot in shots:
        sid = value(shot, 'UniqueID')
        record = one(shot, 'Record')
        start, duration = xml_int(record, 'In'), xml_int(record, 'Duration', 1)
        if sid in ids or start < end:
            raise ValueError('duplicate/overlapping authored shot')
        ids.add(sid)
        end = start + duration
        source = one(shot, 'Source')
        parent_id, source_in = value(source, 'ParentID'), xml_int(source, 'In')
        if parent_id not in sources:
            raise ValueError('authored source ParentID missing')
        parent = sources[parent_id]
        parent_in, parent_duration = xml_int(parent, 'In'), xml_int(parent, 'Duration', 1)
        if rate(parent) != edit_rate or not parent_in <= source_in < parent_in + parent_duration:
            raise ValueError('authored source range/rate mapping mismatch')
        # Later producer still-image shots intentionally hold a one-frame asset
        # for multiple edit units. Do not invent whole-sequence time mapping.
        # The selected acquired movie frame requires an ordinary in-range source.
        if start <= f['index'] < start + duration and source_in + duration > parent_in + parent_duration:
            raise ValueError('selected authored source duration mapping unsupported')
        offsets = set()
        shot_records = records(shot, 'shot', targets)
        for frame in shot.findall('Frame'):
            offset, fid = xml_int(frame, 'EditOffset'), value(frame, 'UniqueID')
            if offset in offsets or offset >= duration or fid in frame_ids:
                raise ValueError('duplicate/out-of-shot authored frame')
            offsets.add(offset)
            frame_ids.add(fid)
            frame_records = records(frame, 'frame', targets)
            if start + offset != f['index']:
                continue
            l1_records = [x for x in frame_records if x['level'] == 1]
            if len(l1_records) != 1:
                raise ValueError('explicit selected frame-local authored L1 required')
            lo, avg, hi = decimals(l1_records[0]['fields'][0]['text'], 3)
            shot_l1 = [x for x in shot_records if x['level'] == 1]
            if shot_l1 and decimals(shot_l1[0]['fields'][0]['text'], 3) != [lo, avg, hi]:
                raise ValueError('conflicting selected frame/shot L1')
            shot_trims = {x['target_id']: x for x in shot_records if x['level'] == 2}
            for trim in (x for x in frame_records if x['level'] == 2):
                if trim['target_id'] in shot_trims and trim['fields'] != shot_trims[trim['target_id']]['fields']:
                    raise ValueError('conflicting selected frame/shot L2 unsupported')
            if not any(x['level'] == 2 and str(x['target_id']) == target_id for x in shot_records + frame_records):
                raise ValueError('selected authored target trim absent')
            mapping = dict(output_id=value(output, 'UniqueID'), track_id=value(t, 'UniqueID'),
                           shot_id=sid, frame_id=fid, source_parent_id=parent_id,
                           source_in=source_in, shot_in=start, shot_duration=duration,
                           edit_offset=offset, edit_rate=edit_rate)
            selected.append((mapping, {'min_pq': lo, 'avg_pq': avg, 'max_pq': hi}, shot_records + frame_records))
    if len(selected) != 1:
        raise ValueError('missing/ambiguous selected authored frame')
    return selected[0]


@validation
def parsed_export(analysis_raw, original_raw, repair_raw, source_path, source_raw, obj):
    source_target(obj['source'], obj['target'])
    root, receipt = repaired(original_raw, analysis_raw, repair_raw)
    association = receipt['source_association']
    _, provenance_raw = retained(source_path.parent, association['provenance'])
    provenance = parse_json(provenance_raw)
    _, producer_global_raw = retained(source_path.parent, association['producer_global'])
    if (provenance['original_xml_sha256'] != sha(original_raw) or
            provenance['producer_global_sha256'] != sha(producer_global_raw) or
            provenance['algorithm_versions_from_producer_global'] != '0,0' or
            association['algorithm_versions'] != '0,0'):
        raise ValueError('source-associated declaration provenance mismatch')
    sequence, selected = source_manifest(source_path, source_raw, obj)
    if (sequence['provenance']['publication']['sha256'] != association['provenance']['sha256'] or
            sequence['provenance']['acquisition']['sha256'] != sha(repair_raw)):
        raise ValueError('sparse source/repair provenance binding mismatch')
    if selected['original']['sha256'] != receipt['originals'][0]['sha256']:
        raise ValueError('authored original frame/repair source identity mismatch')
    argv = receipt['render']['argv']
    if argv.count('-f') != 1 or str(obj['frame']['index']) != argv[argv.index('-f') + 1]:
        raise ValueError('authored selected original frame/acquisition mismatch')
    mapping, l1, preserved_records = selected_metadata(root, obj, sequence)
    return {'schema': 3, 'stage': STAGE, 'analysis_sha256': sha(analysis_raw),
            'original_analysis_sha256': sha(original_raw), 'declaration_repair_sha256': sha(repair_raw),
            'source_manifest_sha256': sha(source_raw), 'source_sha256': obj['frame']['input']['sha256'],
            'frame_index': obj['frame']['index'], 'pts': obj['frame']['pts'],
            'parser': parser_identity(), 'xml_version': '2.0.5', 'algorithm_versions': [0, 0],
            'selected_cm_name': None, 'mapping': mapping, 'l1': l1, 'records': preserved_records,
            'translation': TRANSLATION}


@validation
def metadata(base, envelope, obj):
    keys(envelope, 'origin analysis original_analysis declaration_repair source_manifest export frame_index pts')
    if envelope['origin'] != 'authored-master' or not strict_equal(envelope['frame_index'], obj['frame']['index']) or not strict_equal(envelope['pts'], obj['frame']['pts']):
        raise ValueError('authored metadata frame identity mismatch')
    _, actual = snapshot(base, envelope['analysis'])
    _, original = snapshot(base, envelope['original_analysis'])
    _, repair = snapshot(base, envelope['declaration_repair'])
    source_path, source = snapshot(base, envelope['source_manifest'])
    _, export = snapshot(base, envelope['export'])
    data = parse_json(export)
    keys(data, EXPORT_KEYS)
    expected = parsed_export(actual, original, repair, source_path, source, obj)
    if not strict_equal(data, expected):
        raise ValueError('export differs from bound authored XML/source/parser')
    return {**data, 'max_pq_y': data['l1']['max_pq'], 'avg_pq_y': data['l1']['avg_pq']}


@validation
def validate_alignment(a):
    if a['stage'] != STAGE or a['xml_version'] != '2.0.5' or a['translation'] != TRANSLATION or a['selected_cm_name'] is not None or not strict_equal(a['algorithm_versions'], [0, 0]):
        raise ValueError('unsupported authored baseline alignment')
    for name in ('metadata_sha256', 'analysis_sha256', 'original_analysis_sha256', 'declaration_repair_sha256', 'source_manifest_sha256'):
        digest(a[name])
    keys(a['parser'], 'name version sha256')
    if a['parser'] != parser_identity():
        raise ValueError('authored parser identity mismatch')
    m = a['mapping']
    keys(m, MAPPING_KEYS)
    for k in ('output_id', 'track_id', 'shot_id', 'frame_id', 'source_parent_id'):
        text(m[k])
    for k in ('source_in', 'shot_in', 'edit_offset', 'shot_duration'):
        integer(m[k], 1 if k == 'shot_duration' else 0)
    keys(m['edit_rate'], 'num den')
    n, d = (integer(m['edit_rate'][k], 1) for k in ('num', 'den'))
    if m['edit_offset'] >= m['shot_duration'] or m['shot_in'] + m['edit_offset'] != a['frame_index'] or a['pts']['num'] * n != a['frame_index'] * d * a['pts']['den']:
        raise ValueError('authored mapping/frame/PTS mismatch')


@validation
def reference_provenance(base, repair_binding, obj, metadata, reference_binding):
    """Inspect retained real execution/log snapshots, never invoke a vendor tool.

    Hashes bind retained provenance; they are not an authentication/signature.
    This deliberately accepts only the acquired one-frame baseline receipt.
    """
    _, raw = snapshot(base, repair_binding)
    r = parse_json(raw)
    if sha(raw) != metadata['declaration_repair_sha256'] or r['schema'] != 'hdr.sparks-source-associated-reference.v1':
        raise ValueError('reference declaration receipt mismatch')
    if not (r['render']['exit'] == 0 and type(r['render']['exit']) is int and
            r['validation']['exit'] == 0 and type(r['validation']['exit']) is int and
            r['validation']['validation_overrides'] is False and
            r['render']['metadata_validation'] == 'enabled, default' and
            r['selected_cm_name_from_normal_logs'] is None and
            strict_equal(r['validation']['declared_and_vendor_validated_algorithm_versions'], [0, 0])):
        raise ValueError('normal acquired reference execution evidence required')
    f, target = obj['frame'], obj['target']
    if ((f['width'], f['height'], f['index'], f['pts']) != (4096, 2160, 0, {'num': 0, 'den': 1}) or
            target != {'id': '27', 'min_nits': 0, 'max_nits': 600, 'primaries': P3} or
            obj['source']['mastering'] != {'min_nits': 0.005, 'max_nits': 4000, 'primaries': P3}):
        raise ValueError('reference only acquired original full frame0 target27')
    if (r['new_derivative']['sha256'] != metadata['analysis_sha256'] or
            r['originals'][1]['sha256'] != metadata['original_analysis_sha256'] or
            r['Mac_reference']['sha256'] != reference_binding['sha256'] or
            r['target']['source_xml_sha256'] != metadata['analysis_sha256'] or
            r['target']['target_id'] != 27 or r['target']['verified'] is not True):
        raise ValueError('reference XML/output/target identity mismatch')
    a = r['render']['argv']
    expected = [a[0], '--cpu-only', '-t', '2', '--disable-font-color', '-m',
                r['validation']['command']['argv'][-1], '--source-format',
                'half rgb full pq p3d65', '--output-format', 'half rgb full pq bt2020',
                '-r', '60000/1001', '--targ', '27', '--echo-metadata',
                a[-4], a[-3], '-f', '0']
    if a != expected or metadata['mapping']['edit_rate'] != {'num': 60000, 'den': 1001}:
        raise ValueError('reference argv/frame/rate/encoding mismatch')
    native_identities = r['final_native_readback']['identities']
    identities = {item['path']: item['sha256'] for item in native_identities}
    original_native = a[-4].replace('#####', '00000')
    if (identities.get(original_native) != r['originals'][0]['sha256'] or
            identities.get(a[6]) != metadata['analysis_sha256'] or
            a[0] not in identities or r['validation']['command']['argv'][0] not in identities):
        raise ValueError('reference native source/tool identity absent')
    logs = {}
    for request_id in (r['validation']['request'], r['target_info_request'], r['render_request']):
        entries = [x for x in r['requests'] if x.get('request_id') == request_id]
        if len(entries) != 1 or entries[0].get('exit') != 0 or entries[0].get('ok') is not True:
            raise ValueError('reference command/log entry absent')
        entry = entries[0]['full_output']
        log_path, log = retained(base, entry)
        logs[request_id] = {'file': str(log_path), 'sha256': entry['sha256']}
        contents = log.decode('utf8')
        if request_id == r['validation']['request']:
            required = ['Algorithm version: 0 0', 'No issues found in the Metadata']
        elif request_id == r['target_info_request']:
            required = ['(ID 27)', 'pq(0,600) rgb computer p3d65']
        else:
            required = ['Src Info:', '4096x2160x3 f16 planar 444 le tight 0-0 24fps top_left pq rgb computer p3d65',
                        'Dst Info:', '4096x2160x3 f16 planar 444 le tight 0-0 59.94fps top_left pq rgb computer bt2020',
                        'Frames: 0-0', 'completed 1 frames', reference_binding['sha256']]
        if not all(x in contents for x in required):
            raise ValueError('reference actual normal log evidence mismatch')
    return {'receipt': repair_binding, 'receipt_sha256': sha(raw), 'vendor_argv': a,
            'vendor_runtime_identities': native_identities, 'logs': logs,
            'selected_cm_name': None, 'metadata_application': 'authored L1/L2 by actual vendor reference',
            'label': r['label'], 'scope_limits': r['source_scope_limit'],
            'warnings_and_rate_limits': r['warnings_and_rate_limits'],
            'content_limit': 'original frame0 near-black only; not representative trim/highlight/chroma coverage'}


@validation
def normalize_reference(manifest, reference_exr, output):
    """After review: normalize immutable acquired reference, never render it again."""
    from tools.dolby_harness.contracts import ENCODING, alignment, input_manifest
    from tools.dolby_harness.master_pixels import normalize
    manifest_raw = read_bounded(manifest, 4 * 1024 * 1024)
    obj, _, meta = input_manifest(manifest, manifest_raw)
    if obj['schema'] != 3:
        raise ValueError('authored reference requires schema3 input')
    _, repair_raw = snapshot(Path(manifest).parent, obj['metadata']['declaration_repair'])
    receipt = parse_json(repair_raw)
    reference_binding = {'file': str(Path(reference_exr).resolve()),
                         'sha256': receipt['Mac_reference']['sha256']}
    vendor = reference_provenance(Path(manifest).parent, obj['metadata']['declaration_repair'], obj, meta, reference_binding)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    conversion = normalize(reference_exr, output / 'output.f32', reference_binding['sha256'])
    if (conversion['width'], conversion['height']) != (obj['frame']['width'], obj['frame']['height']):
        raise ValueError('reference geometry mismatch')
    expected = [0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.329]
    chroma = conversion['header']['attributes'].get('chromaticities')
    if chroma != {'type': 'chromaticities', 'hex': struct.pack('<8f', *expected).hex()}:
        raise ValueError('reference BT2020 chromaticities mismatch')
    (output / 'input-manifest.json').write_bytes(manifest_raw)
    # Bind a path to the original input manifest so its relative artifacts remain
    # resolvable; the copied snapshot is archival, not a rebased declaration.
    result = {'schema': 3, 'role': 'reference', 'alignment': alignment(obj, meta),
              'encoding': ENCODING, 'output': {'file': 'output.f32', 'sha256': conversion['normalized']['sha256']},
              'provenance': {'input_manifest': {'file': str(Path(manifest).resolve()), 'sha256': sha(manifest_raw)},
                             'vendor': vendor, 'storage_conversion': conversion}}
    with (output / 'reference.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return output / 'reference.json'


@validation
def validate_result(base, result):
    """Rebind alignment to actual input snapshots before accepting schema3 output."""
    from tools.dolby_harness.contracts import alignment, input_manifest
    provenance = result['provenance']
    manifest, raw = snapshot(base, provenance['input_manifest'])
    obj, _, meta = input_manifest(manifest, raw)
    if obj['schema'] != 3 or not strict_equal(alignment(obj, meta), result['alignment']):
        raise ValueError('authored result/input alignment mismatch')
    if result['role'] == 'reference':
        conversion = provenance['storage_conversion']
        vendor = reference_provenance(manifest.parent, obj['metadata']['declaration_repair'], obj, meta, conversion['original'])
        validate_decoder(conversion['decoder'])
        if not strict_equal(vendor, provenance['vendor']) or conversion['normalized']['sha256'] != result['output']['sha256']:
            raise ValueError('authored reference provenance mismatch')
        _, original = snapshot(base, conversion['original'], 256 * 1024 * 1024)
        _, normalized = snapshot(base, result['output'], geometry(obj['frame']['width'], obj['frame']['height']) * 12)
        actual_header = verify(original, normalized, obj['frame']['width'], obj['frame']['height'])
        if (conversion.get('operation') != 'HALF-exact-binary32-storage-only' or
                conversion.get('entry_point') != 'tools.dolby_harness.master_pixels.normalize' or
                conversion.get('transforms') != [] or conversion.get('header') != actual_header or
                (conversion.get('width'), conversion.get('height')) != (obj['frame']['width'], obj['frame']['height'])):
            raise ValueError('reference storage conversion declaration mismatch')
    else:
        from tools.dolby_harness.harness import baseline_semantics, control
        from tools.dolby_harness.provenance import COMPILE_INPUTS, implementation
        execution = provenance['execution']
        _, compile_raw = snapshot(base, {'file': 'compile-receipt.json',
                                         'sha256': execution['compile_receipt_sha256']})
        compiled = parse_json(compile_raw)
        if not strict_equal(compiled, execution['compile_receipt']) or compiled['binary_sha256'] != execution['native_sha256'] or compiled['runtime'] != execution['runtime']:
            raise ValueError('authored candidate compiler/runtime binding mismatch')
        current = implementation()['sources']
        if execution['frontend']['sources'] != current or any(compiled['sources'][k] != sha(Path(__file__).resolve().parents[2] / k) for k in COMPILE_INPUTS):
            raise ValueError('authored candidate implementation changed')
        _, native_control = snapshot(base, {'file': 'control.txt', 'sha256': provenance['control_sha256']})
        for name in ('stdout', 'stderr'):
            snapshot(base, {'file': 'native.' + name, 'sha256': provenance[name + '_sha256']})
        if native_control != control(obj, meta).encode('utf8') or provenance['protocol'] != 'DVH2' or not strict_equal(provenance['baseline_semantics'], baseline_semantics(obj, meta)):
            raise ValueError('authored candidate control/semantics mismatch')
