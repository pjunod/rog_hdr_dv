#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Compare two raw RGBA dumps of the same picture (8- or 16-bit channels).

usage: compare-dumps.py 8|16 A B
Prints JSON: whether the files are byte-identical, the share of pixels whose
RGB channels are identical, and the largest RGB and alpha differences.
"""
import array
import json
import sys


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
    kind = 'H' if bits == 16 else 'B'
    a, b = array.array(kind, a_bytes), array.array(kind, b_bytes)
    pixels = len(a) // 4
    same = worst = worst_alpha = 0
    for i in range(pixels):
        d = max(abs(a[4 * i + c] - b[4 * i + c]) for c in range(3))
        same += d == 0
        worst = max(worst, d)
        worst_alpha = max(worst_alpha, abs(a[4 * i + 3] - b[4 * i + 3]))
    print(json.dumps({'byte_identical': a_bytes == b_bytes, 'pixels': pixels,
                      'identical_rgb_pct': round(100 * same / pixels, 4),
                      'max_rgb_diff': worst, 'max_alpha_diff': worst_alpha}))
    return 0 if a_bytes == b_bytes else 3


sys.exit(main())
