#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate synthetic colour fixtures and measure a normal sandboxed glycin probe.

Requires numpy, Pillow and liblcms2; writes only below the explicit output path.
The probe is image-pixels.rs compiled against the candidate Loupe dependencies.
No desktop or display settings are changed.
"""
import argparse
import ctypes as C
import ctypes.util
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib

import numpy as np
from PIL import Image, ImageCms


def profile():
    """An RGB profile built from public Adobe RGB (1998) primaries and gamma."""
    class xyY(C.Structure):
        _fields_ = [(x, C.c_double) for x in ('x', 'y', 'Y')]
    class Primaries(C.Structure):
        _fields_ = [(x, xyY) for x in ('Red', 'Green', 'Blue')]
    lib = C.CDLL(ctypes.util.find_library('lcms2'))
    lib.cmsBuildGamma.argtypes = [C.c_void_p, C.c_double]
    lib.cmsBuildGamma.restype = C.c_void_p
    lib.cmsCreateRGBProfile.argtypes = [C.POINTER(xyY), C.POINTER(Primaries), C.POINTER(C.c_void_p)]
    lib.cmsCreateRGBProfile.restype = C.c_void_p
    lib.cmsSaveProfileToMem.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(C.c_uint32)]
    lib.cmsCloseProfile.argtypes = [C.c_void_p]
    lib.cmsFreeToneCurve.argtypes = [C.c_void_p]
    curve = lib.cmsBuildGamma(None, 563 / 256)
    white = xyY(.3127, .3290, 1)
    primaries = Primaries(xyY(.64, .33, 1), xyY(.21, .71, 1), xyY(.15, .06, 1))
    curves = (C.c_void_p * 3)(curve, curve, curve)
    handle = lib.cmsCreateRGBProfile(C.byref(white), C.byref(primaries), curves)
    if not handle:
        raise RuntimeError('lcms2 rejected synthetic profile')
    try:
        size = C.c_uint32()
        assert lib.cmsSaveProfileToMem(handle, None, C.byref(size))
        buf = C.create_string_buffer(size.value)
        assert lib.cmsSaveProfileToMem(handle, buf, C.byref(size))
        # Deliberately retain a 21,012-byte metadata payload: enough to
        # expose the decoder's old per-Value allocation accounting.
        data = buf.raw[:size.value].ljust(21012, b'\0')
        return struct.pack('>I', len(data)) + data[4:]
    finally:
        lib.cmsCloseProfile(handle)
        lib.cmsFreeToneCurve(curve)


def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


def png(path, pixels, depth, icc=None, cicp=None):
    a = np.asarray(pixels, dtype='>u2' if depth == 16 else 'u1')
    channels = a.shape[1]
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', len(a), 1, depth, {3: 2, 4: 6}[channels], 0, 0, 0))
    if icc is not None:
        data += chunk(b'iCCP', b'synthetic\0\0' + zlib.compress(icc))
    if cicp is not None:
        data += chunk(b'cICP', bytes(cicp))
    path.write_bytes(data + chunk(b'IDAT', zlib.compress(b'\0' + a.tobytes())) + chunk(b'IEND', b''))


def tiff(path, colors, size, icc, field=7, malformed=None):
    """Classic little-endian uncompressed RGB TIFF, with explicit ICC field type."""
    colors = np.asarray(colors, dtype='u1')
    row = np.resize(colors, (size, 3)).tobytes()
    count = 11
    end = 8 + 2 + count * 12 + 4
    bits_offset = end
    profile_offset = end + 6
    pixel_offset = profile_offset + len(icc)
    entries = [
        (256, 4, 1, size), (257, 4, 1, size), (258, 3, 3, bits_offset),
        (259, 3, 1, 1), (262, 3, 1, 2), (273, 4, 1, pixel_offset),
        (277, 3, 1, 3), (278, 4, 1, size), (279, 4, 1, size * size * 3),
        (284, 3, 1, 1), (34675, field, len(icc), profile_offset),
    ]
    if malformed == 'offset':
        entries[-1] = (34675, field, len(icc), pixel_offset + size * size * 3 - 2)
    elif malformed == 'count':
        entries[-1] = (34675, field, 0xffffffff, profile_offset)
    header = b'II*\0' + struct.pack('<I', 8) + struct.pack('<H', count)
    header += b''.join(struct.pack('<HHII', *entry) for entry in entries) + struct.pack('<I', 0)
    path.write_bytes(header + struct.pack('<HHH', 8, 8, 8) + icc + row * size)


def matrix(coords):
    m = np.asarray([[x / y, 1, (1 - x - y) / y] for x, y in coords]).T
    return m @ np.diag(np.linalg.solve(m, [.3127 / .329, 1, (1 - .3127 - .329) / .329]))


WIDE = matrix([(.708, .292), (.170, .797), (.131, .046)])
ADOBE = matrix([(.64, .33), (.21, .71), (.15, .06)])
SRGB = matrix([(.64, .33), (.3, .6), (.15, .06)])


def expected(codes, space='adobe', depth=8):
    values = np.asarray(codes, dtype='f8') / ((1 << depth) - 1)
    linear = values ** (563 / 256) if space == 'adobe' else np.where(values <= .04045, values / 12.92, ((values + .055) / 1.055) ** 2.4)
    return linear @ np.linalg.solve(WIDE, ADOBE if space == 'adobe' else SRGB).T


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--loader-data', type=Path, help='Standard deserialized loader config root; sandbox remains enabled')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import os
    env = os.environ.copy()
    if args.loader_data:
        env['GLYCIN_DATA_DIR'] = str(args.loader_data.resolve())
    wide_profile = profile()
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    colors = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255], [255] * 3, [48, 128, 200]])
    grey = np.arange(256)[:, None].repeat(3, 1)
    rgba = np.column_stack([np.full(6, 48), np.full(6, 128), np.full(6, 200), [0, 1, 32, 128, 254, 255]])
    high = np.array([[1, 2, 3], [31, 32, 33], [128, 129, 130], [32768] * 3, [32769] * 3, [60000, 20000, 30000], [65535] * 3])
    results = {}
    def read(name):
        r = subprocess.run([str(args.probe.resolve()), str((args.output / name).resolve())], env=env, capture_output=True, text=True, timeout=60, check=True)
        match = re.search(r' (\d+)x(\d+) ', r.stdout)
        if not match:
            raise RuntimeError(r.stdout + r.stderr)
        values = np.array([[float(v) for v in pixel.split(',')] for pixel in r.stdout[match.end():].split()])
        return values, r.stdout[:match.start()].split(name, 1)[1].strip()
    def measure(name, observed, reference, limit=.0007):
        delta = abs(observed - reference)
        results[name] = {'max_abs_linear': float(np.max(delta)), 'mean_abs_linear': float(np.mean(delta)), 'limit': limit}
        assert results[name]['max_abs_linear'] <= limit, (name, results[name])
    for space, icc in [('adobe', wide_profile), ('srgb', srgb)]:
        for kind, codes in [('primaries', colors), ('ramp', grey)]:
            name = f'{space}-{kind}.png'
            png(args.output / name, codes, 8, icc)
            observed, fmt = read(name)
            measure(name, observed[:, :3], expected(codes, space))
            assert fmt.endswith('R16g16b16Float'), fmt
            if kind == 'ramp':
                results[name]['distinct_gray_levels'] = len(np.unique(observed[:, 1]))
                assert results[name]['distinct_gray_levels'] == 256
    png(args.output / 'rgba.png', rgba, 8, wide_profile)
    observed, fmt = read('rgba.png')
    assert fmt.endswith('R16g16b16a16Float'), fmt
    measure('rgba-alpha', observed[:, 3], rgba[:, 3] / 255)
    measure('rgba-color', observed[1:, :3], expected(rgba[1:, :3]))
    png(args.output / 'sixteen.png', high, 16, wide_profile)
    observed, fmt = read('sixteen.png')
    assert fmt.endswith('R32g32b32Float'), fmt
    measure('sixteen', observed[:, :3], expected(high, depth=16), .0002)
    assert observed[3, 1] != observed[4, 1]
    results['sixteen']['nearby_midtones'] = observed[3:5, 1].tolist()
    rgba16 = np.column_stack([np.full(5, 60000), np.full(5, 20000), np.full(5, 30000), [0, 1, 128, 32768, 65535]])
    png(args.output / 'rgba16.png', rgba16, 16, wide_profile)
    observed, fmt = read('rgba16.png')
    assert fmt.endswith('R32g32b32a32Float'), fmt
    measure('rgba16-alpha', observed[:, 3], rgba16[:, 3] / 65535, .0000001)
    measure('rgba16-color', observed[1:, :3], expected(rgba16[1:, :3], depth=16), .0002)
    for name, icc, cicp in [('both.png', wide_profile, (12, 13, 0, 1)), ('cicp.png', None, (12, 13, 0, 1)), ('bad.png', b'not an ICC profile', None), ('untagged.png', None, None)]:
        png(args.output / name, colors, 8, icc, cicp)
    measure('cicp-precedence', read('both.png')[0], read('cicp.png')[0], 0)
    measure('invalid-icc-fallback', read('bad.png')[0], read('untagged.png')[0], 0)
    for size in (80, 320, 1024):
        for field in (1, 7):
            name = f'tiff-{size}-type{field}.tif'
            tiff(args.output / name, colors, size, wide_profile, field)
            observed, fmt = read(name)
            assert fmt.endswith('R16g16b16Float'), fmt
            measure(name, observed[:, :3], expected(np.resize(colors, (size, 3))))
    for failure in ('offset', 'count'):
        name = f'tiff-malformed-{failure}.tif'
        tiff(args.output / name, colors, 80, wide_profile, malformed=failure)
        observed, fmt = read(name)
        measure(name, observed[:, :3], expected(np.resize(colors, (80, 3)), 'srgb'), .0007)
        results[name]['behavior'] = 'invalid metadata falls back to sRGB; image still decodes'
    image = Image.fromarray(np.tile(np.repeat(colors.astype('u1'), 16, axis=0)[None, :, :], (8, 1, 1)))
    image.save(args.output / 'blocks.jpg', icc_profile=wide_profile, quality=100, subsampling=0)
    observed, _ = read('blocks.jpg')
    measure('jpeg', observed[8::16, :3], expected(colors), .012)
    (args.output / 'receipts.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
