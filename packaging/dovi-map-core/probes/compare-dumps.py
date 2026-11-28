#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Compare two raw RGBA dumps of the same picture.

usage: compare-dumps.py 8|16|10 A B
  8, 16  RGBA with 8- or 16-bit channels
  10     DRM_FORMAT_ABGR2101010 words (R in bits 0-9) in both files
Prints JSON: whether the files are byte-identical, the share of pixels whose
RGB channels are identical, the largest RGB and alpha differences and, when
they differ, a histogram of each pixel's largest RGB difference, in the
files' own code values.
"""
import array
import json
import sys


def channels(data, bits):
    if bits == 10:
        out = array.array('H')
        for w in array.array('I', data):
            out.extend((w & 1023, (w >> 10) & 1023, (w >> 20) & 1023, w >> 30))
        return out
    return array.array('H' if bits == 16 else 'B', data)


def main():
    bits, a_path, b_path = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    a_bytes, b_bytes = open(a_path, 'rb').read(), open(b_path, 'rb').read()
    if len(a_bytes) != len(b_bytes):
        print(json.dumps({'error': 'size differs', 'a': len(a_bytes), 'b': len(b_bytes)}))
        return 1
    pixel_bytes = 8 if bits == 16 else 4
    if a_bytes == b_bytes:
        print(json.dumps({'byte_identical': True, 'pixels': len(a_bytes) // pixel_bytes,
                          'identical_rgb_pct': 100.0, 'max_rgb_diff': 0, 'max_alpha_diff': 0}))
        return 0
    a, b = channels(a_bytes, bits), channels(b_bytes, bits)
    pixels = len(a) // 4
    same = worst = worst_alpha = 0
    histogram = {}
    for i in range(pixels):
        d = max(abs(a[4 * i + c] - b[4 * i + c]) for c in range(3))
        same += d == 0
        worst = max(worst, d)
        histogram[d] = histogram.get(d, 0) + 1
        worst_alpha = max(worst_alpha, abs(a[4 * i + 3] - b[4 * i + 3]))
    print(json.dumps({'byte_identical': False, 'pixels': pixels,
                      'identical_rgb_pct': round(100 * same / pixels, 4),
                      'max_rgb_diff': worst, 'max_alpha_diff': worst_alpha,
                      'max_diff_histogram': {str(k): v for k, v in sorted(histogram.items())}}))
    return 3


sys.exit(main())
