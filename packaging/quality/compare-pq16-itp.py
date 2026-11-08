#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""BT.2124 digital comparison of full-range BT.2020/PQ RGB16LE frames.

Normative method: ITU-R BT.2124-0 Annex 1, with Annex 2 conversion 3.
https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2124-0-201901-I!!PDF-E.pdf
This measures serialized digital outputs, not a physical display or conformance.
"""
import argparse
import json
import os
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import numpy as np

M1 = 2610 / 16384
M2 = 2523 / 32
C1 = 3424 / 4096
C2 = 2413 / 128
C3 = 2392 / 128
RGB_TO_LMS = np.array([[1688, 2146, 262], [683, 2951, 462],
                       [99, 309, 3688]], dtype=np.float64) / 4096
LMS_TO_ICTCP = np.array([[2048, 2048, 0], [6610, -13613, 7003],
                         [17933, -17390, -543]], dtype=np.float64) / 4096


def pq_to_relative_linear(code):
    """PQ inverse to linear luminance relative to 10000 cd/m2."""
    power = np.power(code, 1 / M2)
    return np.power(np.maximum(power - C1, 0) / (C2 - C3 * power), 1 / M1)


def relative_linear_to_pq(linear):
    power = np.power(linear, M1)
    return np.power((C1 + C2 * power) / (1 + C3 * power), M2)


def rgb_pq_to_itp(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    if np.any(~np.isfinite(rgb)) or np.any(rgb < 0) or np.any(rgb > 1):
        raise ValueError('Expected finite normalized full-range PQ RGB')
    lms = pq_to_relative_linear(rgb) @ RGB_TO_LMS.T
    itp = relative_linear_to_pq(lms) @ LMS_TO_ICTCP.T
    itp[..., 1] *= 0.5
    return itp


def distance(first, second):
    delta = first - second
    return 720 * np.sqrt(np.sum(delta * delta, axis=-1))


def self_test():
    # Published BT.2124 Annex 4 blue-patch conversion and rounded ITP example.
    reference = rgb_pq_to_itp(np.array([296, 201, 582]) / 1023)
    np.testing.assert_allclose(reference, [0.3554, 0.1346, -0.1613], atol=5e-4,
                               rtol=0)
    # Annex 4 illustration is approximate: exact 10-bit fractions differ by
    # about 3.2e-4 in I. Normative Annex 1 constants are unchanged. Independently
    # require neutral-axis preservation at tight numerical precision.
    gray = np.array([.1, .5, .9])
    neutral = rgb_pq_to_itp(np.repeat(gray[:, None], 3, axis=1))
    np.testing.assert_allclose(neutral[:, 0], gray, atol=1e-12, rtol=0)
    np.testing.assert_allclose(neutral[:, 1:], 0, atol=1e-12, rtol=0)
    rounded = distance(np.array([0.3554, 0.1346, -0.1613]),
                       np.array([0.3568, 0.1321, -0.1629]))
    np.testing.assert_allclose(rounded, 2.363, atol=0.0002, rtol=0)
    identical = rgb_pq_to_itp(np.array([[0, 0, 0], [1, 1, 1], [.4, .2, .7]]))
    assert np.array_equal(distance(identical, identical), np.zeros(3))


def compare(first_path, second_path, width, height, block_pixels=65536):
    count = width * height
    expected_bytes = count * 3 * 2
    if width <= 0 or height <= 0:
        raise ValueError('Positive fixed image dimensions required')
    for path in (first_path, second_path):
        if Path(path).stat().st_size != expected_bytes:
            raise ValueError('Raw frame size does not match declared geometry')
    first = np.memmap(first_path, dtype='<u2', mode='r', shape=(count, 3))
    second = np.memmap(second_path, dtype='<u2', mode='r', shape=(count, 3))
    differences = np.empty(count, dtype=np.float64)
    for start in range(0, count, block_pixels):
        stop = min(start + block_pixels, count)
        left = rgb_pq_to_itp(first[start:stop].astype(np.float64) / 65535)
        right = rgb_pq_to_itp(second[start:stop].astype(np.float64) / 65535)
        differences[start:stop] = distance(left, right)
    assert np.all(np.isfinite(differences))
    return {
        'pixels': count,
        'mean': float(np.mean(differences)),
        'median': float(np.quantile(differences, .5, method='linear')),
        'p95': float(np.quantile(differences, .95, method='linear')),
        'p99': float(np.quantile(differences, .99, method='linear')),
        'max': float(np.max(differences)),
        'fraction_gt1': float(np.mean(differences > 1)),
        'fraction_gt3': float(np.mean(differences > 3)),
        'fraction_gt10': float(np.mean(differences > 10)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--height', type=int, required=True)
    args = parser.parse_args()
    self_test()
    result = compare(args.reference, args.candidate, args.width, args.height)
    print(json.dumps({'metric': 'BT.2124 DeltaE_ITP', 'self_test': 'PASS',
                      'normalization': 'RGB16LE/65535, full BT.2020/PQ',
                      'statistics': result}, indent=2))


if __name__ == '__main__':
    main()
