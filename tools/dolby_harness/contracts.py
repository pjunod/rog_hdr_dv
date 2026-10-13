"""Strict, hash-bound stage-1 frame/metadata and private reference contracts."""
import hashlib
import json
import math
from pathlib import Path
import struct

ENCODING = {'layout': 'rgb-f32le', 'orientation': 'top-left', 'range': 'full',
            'matrix': 'rgb', 'transfer': 'pq', 'primaries': 'bt2020'}
MAX_PIXELS = 3840 * 2160


def keys(obj, names):
    if not isinstance(obj, dict) or set(obj) != set(names.split()):
        raise ValueError('missing or unknown contract fields: ' + names)


def integer(x, low=0, high=2**53 - 1):
    if type(x) is not int or not low <= x <= high:
        raise ValueError('integer outside supported domain')
    return x


def number(x, low, high):
    if type(x) not in (int, float) or not math.isfinite(x) or not low <= x <= high:
        raise ValueError('number outside finite supported domain')
    # Native protocol uses IEEE754 float32; reject values it cannot represent.
    if not math.isfinite(struct.unpack('<f', struct.pack('<f', x))[0]):
        raise ValueError('not representable as float32')
    return x


def text(x):
    if not isinstance(x, str) or not x or len(x) > 1024:
        raise ValueError('nonempty bounded identity required')
    return x


def digest(x):
    if not isinstance(x, str) or len(x) != 64 or any(c not in '0123456789abcdef' for c in x):
        raise ValueError('lowercase SHA256 required')
    return x


def parse_json(data):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def load_json(path):
    return parse_json(Path(path).read_bytes())


def bound_file(base, obj):
    keys(obj, 'file sha256')
    p = Path(base) / text(obj['file'])
    digest(obj['sha256'])
    if not p.is_file():
        raise ValueError('required frame/metadata/reference input absent')
    if hashlib.sha256(p.read_bytes()).hexdigest() != obj['sha256']:
        raise ValueError('input SHA256 mismatch')
    return p


def primaries(values):
    if not isinstance(values, list) or len(values) != 8:
        raise ValueError('primaries require rx ry gx gy bx by wx wy')
    for x, y in zip(values[::2], values[1::2]):
        number(x, 0.000001, 0.999999)
        number(y, 0.000001, 0.999999)
        if x + y > 1.000001:
            raise ValueError('unphysical xy')
    rx, ry, gx, gy, bx, by, wx, wy = values
    det = (gy - by) * (rx - bx) + (bx - gx) * (ry - by)
    if abs(det) < 0.000001:
        raise ValueError('degenerate primaries')
    r = ((gy - by) * (wx - bx) + (bx - gx) * (wy - by)) / det
    g = ((by - ry) * (wx - bx) + (rx - bx) * (wy - by)) / det
    if min(r, g, 1 - r - g) <= 0:
        raise ValueError('white outside primary triangle')
    return values


def luminance(obj):
    lo = number(obj['min_nits'], 0, 10000)
    hi = number(obj['max_nits'], 0.000001, 10000)
    if lo >= hi:
        raise ValueError('minimum must be below maximum')
    primaries(obj['primaries'])


def floats(values, shape, low=-1e6, high=1e6):
    if not isinstance(values, list) or len(values) != shape[0]:
        raise ValueError('metadata array shape mismatch')
    if len(shape) == 1:
        return [number(x, low, high) for x in values]
    return [floats(x, shape[1:], low, high) for x in values]


def dovi_metadata(base, obj, frame):
    keys(obj, 'export rpu origin frame_index pts')
    integer(obj['frame_index'])
    keys(obj['pts'], 'num den')
    integer(obj['pts']['num'], -2**53 + 1)
    integer(obj['pts']['den'], 1)
    if obj['origin'] not in ('owned-real-content', 'dolby-tools'):
        raise ValueError('real metadata provenance required; synthetic RPU forbidden')
    if obj['frame_index'] != frame['index'] or obj['pts'] != frame['pts']:
        raise ValueError('metadata frame alignment mismatch')
    export = bound_file(base, obj['export'])
    bound_file(base, obj['rpu'])
    raw = export.read_bytes()
    if hashlib.sha256(raw).hexdigest() != obj['export']['sha256']:
        raise ValueError('metadata changed while loading')
    data = parse_json(raw)
    keys(data, 'schema profile residual_disabled bl_bit_depth nonlinear_offset nonlinear linear comp max_pq_y avg_pq_y')
    if type(data['schema']) is not int or data['schema'] != 1:
        raise ValueError('unknown parsed metadata schema')
    integer(data['profile'], 5, 8)
    if data['profile'] not in (5, 8) or data['residual_disabled'] is not True:
        raise ValueError('only Profile5/8 residual-disabled metadata is supported')
    integer(data['bl_bit_depth'], 8, 16)
    floats(data['nonlinear_offset'], (3,))
    floats(data['nonlinear'], (3, 3))
    floats(data['linear'], (3, 3))
    number(data['max_pq_y'], 0, 1)
    number(data['avg_pq_y'], 0, data['max_pq_y'])
    if not isinstance(data['comp'], list) or len(data['comp']) != 3:
        raise ValueError('three reshape components required')
    for comp in data['comp']:
        keys(comp, 'pivots segments')
        if not isinstance(comp['pivots'], list) or len(comp['pivots']) not in (0, 2, 3, 4, 5, 6, 7, 8, 9):
            raise ValueError('0 or 2..9 pivots required')
        pivots = floats(comp['pivots'], (len(comp['pivots']),), 0, 1)
        if any(a >= b for a, b in zip(pivots, pivots[1:])):
            raise ValueError('strictly increasing pivots required')
        native_pivots = [struct.unpack('<f', struct.pack('<f', x))[0] for x in pivots]
        if any(a >= b for a, b in zip(native_pivots, native_pivots[1:])):
            raise ValueError('pivots collapse at native float32 precision')
        if not isinstance(comp['segments'], list) or len(comp['segments']) != max(len(pivots) - 1, 0):
            raise ValueError('reshape segment count mismatch')
        for seg in comp['segments']:
            if not isinstance(seg, dict):
                raise ValueError('reshape segment object required')
            if seg.get('method') == 'polynomial':
                keys(seg, 'method coefficients')
                floats(seg['coefficients'], (3,))
            elif seg.get('method') == 'mmr':
                keys(seg, 'method order constant coefficients')
                integer(seg['order'], 1, 3)
                number(seg['constant'], -1e6, 1e6)
                floats(seg['coefficients'], (seg['order'], 7))
            else:
                raise ValueError('unknown reshaping method')
    return data


def pixels(path, width, height, expected_sha256=None):
    data = Path(path).read_bytes()
    if expected_sha256 is not None and hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('pixel bytes changed while loading')
    if len(data) != width * height * 12:
        raise ValueError('exact tightly packed RGB-f32le byte count required')
    out = list(struct.iter_unpack('<fff', data))
    if not all(math.isfinite(x) and 0 <= x <= 1 for p in out for x in p):
        raise ValueError('finite normalized samples required (no implicit clipping)')
    return out


def source_target(s, t):
    # Dolby range is an attestation of original base-layer codes, not a request
    # for pre-expansion: upstream RPU matrices/offsets own effective levels.
    # PQ minima remain requested declarations, not guaranteed mapper endpoints.
    keys(s, 'system transfer primaries range bit_depth layout orientation mastering')
    integer(s['bit_depth'], 8, 16)
    if s['bit_depth'] not in (8, 10, 12, 16):
        raise ValueError('supported normalization bit depths are 8/10/12/16')
    if s['system'] not in ('rgb', 'bt2020nc', 'dolbyvision') or s['range'] not in ('full', 'limited'):
        raise ValueError('unsupported matrix/range')
    if (s['transfer'], s['primaries'], s['layout'], s['orientation']) != ('pq', 'bt2020', 'c3-f32le', 'top-left'):
        raise ValueError('unsupported source interpretation; explicit conversion required')
    keys(s['mastering'], 'min_nits max_nits primaries')
    luminance(s['mastering'])
    keys(t, 'id min_nits max_nits primaries')
    text(t['id'])
    luminance(t)


def input_manifest(path, snapshot=None):
    obj = parse_json(Path(path).read_bytes() if snapshot is None else snapshot)
    keys(obj, 'schema frame source target metadata')
    if type(obj['schema']) is not int or obj['schema'] != 1:
        raise ValueError('unknown harness schema')
    f = obj['frame']
    keys(f, 'input width height index pts content_id')
    w, h = integer(f['width'], 1, 3840), integer(f['height'], 1, 2160)
    if w * h > MAX_PIXELS:
        raise ValueError('stage1 frame size bound exceeded')
    integer(f['index'])
    text(f['content_id'])
    keys(f['pts'], 'num den')
    integer(f['pts']['num'], -2**53 + 1)
    integer(f['pts']['den'], 1)
    p = bound_file(Path(path).parent, f['input'])
    pixels(p, w, h, f['input']['sha256'])
    s = obj['source']
    t = obj['target']
    source_target(s, t)
    metadata = None
    if s['system'] == 'dolbyvision':
        metadata = dovi_metadata(Path(path).parent, obj['metadata'], f)
        if metadata['bl_bit_depth'] != s['bit_depth']:
            raise ValueError('RPU base-layer bit depth/source normalization mismatch')
    elif obj['metadata'] is not None:
        raise ValueError('metadata requires explicit dolbyvision interpretation')
    return obj, p, metadata


def alignment(obj):
    f = obj['frame']
    # File paths are local transport, never comparison identities.
    m = obj['metadata']
    return {'content_id': f['content_id'], 'source_sha256': f['input']['sha256'],
            'width': f['width'], 'height': f['height'], 'frame_index': f['index'],
            'pts': f['pts'], 'source': obj['source'], 'target': obj['target'],
            'metadata_sha256': m['export']['sha256'] if m else None,
            'rpu_sha256': m['rpu']['sha256'] if m else None}


def result_manifest(path, snapshot=None):
    obj = parse_json(Path(path).read_bytes() if snapshot is None else snapshot)
    keys(obj, 'schema role alignment encoding output provenance')
    if type(obj['schema']) is not int or obj['schema'] != 1 or obj['role'] not in ('candidate', 'reference'):
        raise ValueError('unknown result contract')
    if obj['encoding'] != ENCODING:
        raise ValueError('reference/candidate encoding mismatch')
    a = obj['alignment']
    keys(a, 'content_id source_sha256 width height frame_index pts source target metadata_sha256 rpu_sha256')
    w, h = integer(a['width'], 1, 3840), integer(a['height'], 1, 2160)
    text(a['content_id'])
    digest(a['source_sha256'])
    integer(a['frame_index'])
    keys(a['pts'], 'num den')
    integer(a['pts']['num'], -2**53 + 1)
    integer(a['pts']['den'], 1)
    source_target(a['source'], a['target'])
    if a['source']['system'] == 'dolbyvision':
        digest(a['metadata_sha256'])
        digest(a['rpu_sha256'])
    elif a['metadata_sha256'] is not None or a['rpu_sha256'] is not None:
        raise ValueError('unexpected metadata identity')
    if not isinstance(obj['provenance'], dict) or not obj['provenance']:
        raise ValueError('renderer/reference provenance required')
    p = bound_file(Path(path).parent, obj['output'])
    return obj, pixels(p, w, h, obj['output']['sha256'])
