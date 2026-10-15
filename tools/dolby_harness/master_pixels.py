"""Storage-only scanline EXR HALF -> packed RGB binary32, without colour math.

A deliberately bounded decoder for single-part RGB HALF, uncompressed or ZIP.
No image-library transfer defaults, integer divisor, gamut/EOTF, clamp or scale.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

from tools.dolby_harness.contracts import digest, integer, keys, text

MAX_WIDTH, MAX_HEIGHT = 4096, 2160
MAX_FILE = 256 * 1024 * 1024
VERSION = '1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def geometry(width, height):
    integer(width, 1, MAX_WIDTH)
    integer(height, 1, MAX_HEIGHT)
    return width * height


def read_bounded(path, maximum=MAX_FILE):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('authored artifact resource bound exceeded')
    return raw


def decoder_identity():
    return {'name': 'dolby-harness-storage-exr', 'version': VERSION,
            'sha256': sha(Path(__file__).read_bytes()),
            'python_version': sys.version,
            'python_sha256': sha(Path(sys.executable).resolve().read_bytes()),
            'zlib_version': zlib.ZLIB_RUNTIME_VERSION}


def validate_decoder(identity):
    # Conversion may have happened on a different host/interpreter. Bind its
    # actual historical runtime, but require the same storage decoder source.
    keys(identity, 'name version sha256 python_version python_sha256 zlib_version')
    current = decoder_identity()
    if any(identity[k] != current[k] for k in ('name', 'version', 'sha256')):
        raise ValueError('storage decoder implementation mismatch')
    digest(identity['python_sha256'])
    text(identity['python_version'])
    text(identity['zlib_version'])


def _cstring(raw, at):
    end = raw.find(b'\0', at, at + 256)
    if end < at:
        raise ValueError('invalid bounded EXR string')
    try:
        return raw[at:end].decode('ascii'), end + 1
    except UnicodeDecodeError as exc:
        raise ValueError('EXR ASCII name required') from exc


def header(raw):
    if len(raw) < 8 or struct.unpack_from('<II', raw) != (20000630, 2):
        raise ValueError('only single-part scanline EXR version2 supported')
    at, attrs = 8, {}
    while True:
        name, at = _cstring(raw, at)
        if not name:
            break
        typ, at = _cstring(raw, at)
        if at + 4 > len(raw):
            raise ValueError('truncated EXR header')
        size, = struct.unpack_from('<I', raw, at)
        at += 4
        if name in attrs or size > 1048576 or at + size > len(raw) or at + size > 1048576:
            raise ValueError('duplicate/truncated/oversized EXR attribute')
        attrs[name] = (typ, raw[at:at + size])
        at += size

    def attr(name, typ, size=None):
        item = attrs.get(name)
        if item is None or item[0] != typ or (size is not None and len(item[1]) != size):
            raise ValueError('missing/invalid EXR ' + name)
        return item[1]

    box = struct.unpack('<4i', attr('dataWindow', 'box2i', 16))
    if box[:2] != (0, 0) or attr('displayWindow', 'box2i', 16) != attrs['dataWindow'][1]:
        raise ValueError('full zero-origin EXR data/display window required')
    width, height = box[2] + 1, box[3] + 1
    geometry(width, height)
    if attr('lineOrder', 'lineOrder', 1) != b'\0':
        raise ValueError('top-left increasing EXR scanlines required')
    if struct.unpack('<f', attr('pixelAspectRatio', 'float', 4))[0] != 1:
        raise ValueError('square EXR pixels required')
    compression = attr('compression', 'compression', 1)[0]
    if compression not in (0, 3):
        raise ValueError('only uncompressed or ZIP EXR storage supported')
    channels_raw = attr('channels', 'chlist')
    channels, pos = [], 0
    while True:
        name, pos = _cstring(channels_raw, pos)
        if not name:
            break
        if pos + 16 > len(channels_raw):
            raise ValueError('truncated EXR channel')
        ptype, linear, xs, ys = struct.unpack_from('<iB3xii', channels_raw, pos)
        if ptype != 1 or linear != 0 or xs != 1 or ys != 1:
            raise ValueError('unsubsampled named RGB HALF storage required')
        channels.append(name)
        pos += 16
    if channels != ['B', 'G', 'R'] or pos != len(channels_raw):
        raise ValueError('exact B/G/R EXR channels required')
    public_attrs = {k: {'type': v[0], 'hex': v[1].hex()} for k, v in attrs.items()}
    return {'width': width, 'height': height, 'channels': channels,
            'compression': compression, 'header_bytes': at, 'attributes': public_attrs}


def _unzip(packed, expected):
    if len(packed) == expected:
        return packed  # EXR stores incompressible blocks verbatim.
    if len(packed) > expected:
        raise ValueError('oversized EXR ZIP block')
    decoder = zlib.decompressobj()
    data = bytearray(decoder.decompress(packed, expected + 1))
    if len(data) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('invalid/oversized EXR ZIP payload')
    # Invert the ZIP byte predictor, then even/odd byte deinterleaving.
    for i in range(1, len(data)):
        data[i] = (data[i - 1] + data[i] - 128) & 255
    half = (expected + 1) // 2
    out = bytearray(expected)
    out[::2], out[1::2] = data[:half], data[half:]
    return out


def decode(raw):
    """Return exact HALF expansion; all validation precedes any output creation."""
    h = header(raw)
    w, height = h['width'], h['height']
    rows = 16 if h['compression'] == 3 else 1
    blocks = (height + rows - 1) // rows
    table_end = h['header_bytes'] + blocks * 8
    if table_end > len(raw):
        raise ValueError('truncated EXR offset table')
    result = bytearray(w * height * 12)
    spans = []
    for block in range(blocks):
        off, = struct.unpack_from('<Q', raw, h['header_bytes'] + block * 8)
        if off < table_end or off + 8 > len(raw):
            raise ValueError('invalid EXR chunk offset')
        y, size = struct.unpack_from('<iI', raw, off)
        if y != block * rows or off + 8 + size > len(raw):
            raise ValueError('ambiguous/truncated EXR scanline chunk')
        count = min(rows, height - y)
        expected = w * count * 6
        packed = raw[off + 8:off + 8 + size]
        data = _unzip(packed, expected) if h['compression'] == 3 else packed
        if len(data) != expected:
            raise ValueError('wrong EXR scanline byte count')
        spans.append((off, off + 8 + size))
        for row in range(count):
            # Each scanline has B,G,R planes; destination is interleaved R,G,B.
            for c in range(3):
                start = (row * 3 + c) * w * 2
                dest = ((y + row) * w) * 12 + (2 - c) * 4
                for i, (v,) in enumerate(struct.iter_unpack('<e', data[start:start + w * 2])):
                    if not math.isfinite(v) or not 0 <= v <= 1:
                        raise ValueError('finite normalized HALF samples required; no clipping')
                    struct.pack_into('<f', result, dest + i * 12, v)
    spans.sort()
    if not spans or spans[0][0] != table_end or spans[-1][1] != len(raw) or any(a[1] != b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('overlap/gap/trailing EXR storage')
    return h, result


def verify(original, normalized, width, height):
    """Independently decode original, not merely trust a conversion attestation."""
    geometry(width, height)
    h, expanded = decode(original)
    if (h['width'], h['height']) != (width, height) or normalized != expanded:
        raise ValueError('original HALF/normalized exact sample or geometry mismatch')
    return h


def normalize(source, output, expected_sha256):
    raw = read_bounded(source)
    if sha(raw) != expected_sha256:
        raise ValueError('EXR source SHA256 mismatch')
    h, expanded = decode(raw)
    receipt = {'schema': 3, 'operation': 'HALF-exact-binary32-storage-only',
               'original': {'file': str(Path(source).resolve()), 'sha256': sha(raw)},
               'normalized': {'file': str(Path(output).resolve()), 'sha256': sha(expanded)},
               'width': h['width'], 'height': h['height'], 'header': h,
               'decoder': decoder_identity(),
               'argv': [sys.executable, *sys.argv],
               'entry_point': 'tools.dolby_harness.master_pixels.normalize',
               'signal_authority': 'external producer/vendor provenance; header defaults are not transfer authority',
               'transforms': []}
    with Path(output).open('xb') as stream:
        stream.write(expanded)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('output')
    p.add_argument('--sha256', required=True)
    p.add_argument('--receipt', required=True)
    args = p.parse_args()
    if Path(args.receipt).exists() or Path(args.output).exists():
        raise ValueError('never overwrite conversion artifacts')
    receipt = normalize(args.source, args.output, args.sha256)
    with Path(args.receipt).open('x') as stream:
        stream.write(json.dumps(receipt, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
