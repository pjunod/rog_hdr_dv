#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare authored-minus-neutral digital ITP responses, without fitting.

Inputs are full-range BT.2020/PQ RGB16LE. Uses compare-pq16-itp.py beside
this file. Bands use the official authored output's maximum linear RGB channel,
not photometric Y. Signed ITP response is authored minus documented neutral.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import numpy as np


def load_method():
    spec = importlib.util.spec_from_file_location(
        'pq16_itp', Path(__file__).with_name('compare-pq16-itp.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.self_test()
    return module


def statistics(values):
    return {'pixels': int(values.size), 'mean': float(np.mean(values)),
            'median': float(np.quantile(values, .5, method='linear')),
            'p95': float(np.quantile(values, .95, method='linear')),
            'p99': float(np.quantile(values, .99, method='linear')),
            'max': float(np.max(values)),
            'fraction_gt3': float(np.mean(values > 3))}


def response(method, paths, width, height):
    count = width * height
    if width <= 0 or height <= 0:
        raise ValueError('Positive dimensions required')
    for path in paths:
        if path.stat().st_size != count * 6:
            raise ValueError('Raw input size differs from declared geometry')
    frames = [np.memmap(p, dtype='<u2', mode='r', shape=(count, 3)) for p in paths]
    primary = np.empty(count)
    neutral_error = np.empty(count)
    response_error = np.empty(count)
    official_effect = np.empty(count)
    candidate_effect = np.empty(count)
    peak = np.empty(count)
    chroma = np.empty(count)
    signed_sum = np.zeros((2, 3))
    response_dot = 0.0
    squared_norm = np.zeros(2)
    active = agreement = 0
    for start in range(0, count, 65536):
        end = min(start + 65536, count)
        rgb = [x[start:end].astype(np.float64) / 65535 for x in frames]
        official, official_neutral, candidate, candidate_neutral = [
            method.rgb_pq_to_itp(x) for x in rgb]
        left = official - official_neutral
        right = candidate - candidate_neutral
        sl = slice(start, end)
        primary[sl] = method.distance(official, candidate)
        neutral_error[sl] = method.distance(official_neutral, candidate_neutral)
        response_error[sl] = method.distance(left, right)
        official_effect[sl] = 720 * np.linalg.norm(left, axis=1)
        candidate_effect[sl] = 720 * np.linalg.norm(right, axis=1)
        peak[sl] = np.max(method.pq_to_relative_linear(rgb[0]), axis=1) * 10000
        chroma[sl] = np.linalg.norm(official[:, 1:], axis=1)
        signed_sum += [np.sum(left, axis=0), np.sum(right, axis=0)]
        response_dot += float(np.sum(left * right))
        squared_norm += [np.sum(left * left), np.sum(right * right)]
        mask = np.abs(left[:, 0]) > 1e-5
        active += int(np.sum(mask))
        agreement += int(np.sum((left[mask, 0] * right[mask, 0]) > 0))
    result = {
        'authored_residual': statistics(primary),
        'neutral_residual': statistics(neutral_error),
        'creative_response_disagreement': statistics(response_error),
        'official_creative_effect': statistics(official_effect),
        'candidate_creative_effect': statistics(candidate_effect),
        'mean_signed_itp_response': {'official': (signed_sum[0]/count).tolist(),
                                     'candidate': (signed_sum[1]/count).tolist()},
        'global_response_cosine': float(response_dot / np.sqrt(np.prod(squared_norm)))
            if np.all(squared_norm > 0) else None,
        'intensity_direction_agreement': agreement / active if active else None,
        'intensity_active_pixels': active,
    }
    for key, values, edges in [
        ('official_peak_rgb_cd_m2_bands', peak, [0, 1, 10, 50, 100.1]),
        ('official_itp_chroma_radius_bands', chroma, [0, .02, .08, 1])]:
        bands = []
        for low, high in zip(edges, edges[1:]):
            mask = (values >= low) & (values < high)
            if np.any(mask):
                bands.append({'low_inclusive': low, 'high_exclusive': high,
                              'authored_residual': statistics(primary[mask]),
                              'response_disagreement': statistics(response_error[mask])})
        result[key] = bands
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['official_authored', 'official_neutral',
                 'candidate_authored', 'candidate_neutral']:
        parser.add_argument(name, type=Path)
    parser.add_argument('--width', type=int, required=True)
    parser.add_argument('--height', type=int, required=True)
    args = parser.parse_args()
    paths = [args.official_authored, args.official_neutral,
             args.candidate_authored, args.candidate_neutral]
    print(json.dumps(response(load_method(), paths, args.width, args.height), indent=2))


if __name__ == '__main__':
    main()
