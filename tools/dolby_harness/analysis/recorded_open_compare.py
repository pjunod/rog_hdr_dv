"""Comparison-only correction for immutable OPEN prepared-curve executions.

Run in a fresh interpreter with an archived rendering frontend. Reproduce its
strict result checks, except serialize/parse the expected algorithm before exact
comparison (tuples in Python are arrays in JSON). Never edit a result, patch a
module, render pixels, relax types/numerics, or change metric.compare_pixels.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare_recorded(renderer_root, candidate, reference):
    renderer_root = Path(renderer_root).resolve(strict=True)
    if any(k.startswith('tools.dolby_harness') for k in sys.modules):
        raise ValueError('fresh interpreter required; no preloaded frontend')
    sys.path.insert(0, str(renderer_root))
    from tools.dolby_harness import authored_master as am, open_dm, open_dm_provenance as prov
    from tools.dolby_harness.contracts import ENCODING, alignment, input_manifest, parse_json, result_manifest
    from tools.dolby_harness.master_pixels import read_bounded
    from tools.dolby_harness.metric import compare_pixels

    for module in (am, open_dm, prov):
        if not Path(module.__file__).resolve().is_relative_to(renderer_root):
            raise ValueError('module escaped archived rendering frontend')
    candidate = Path(candidate)
    reference = Path(reference)
    raw = read_bounded(candidate, 4 * 1024 * 1024)
    r = parse_json(raw)
    am.keys(r, 'schema role source_alignment encoding output algorithm provenance')
    if r['schema'] != open_dm.SCHEMA or r['role'] != 'candidate' or not am.strict_equal(r['encoding'], ENCODING):
        raise ValueError('OPEN result schema/role/encoding mismatch')
    p = r['provenance']
    manifest, input_raw = am.snapshot(candidate.parent, p['input_manifest'])
    obj, _, meta = input_manifest(manifest, input_raw)
    if not am.strict_equal(r['source_alignment'], alignment(obj, meta)):
        raise ValueError('OPEN source alignment mismatch')
    variant = r['algorithm']['variant']
    # Sole difference from the archived validate_result metadata predicate.
    expected = json.loads(json.dumps(open_dm.algorithm(obj, meta, variant), allow_nan=False))
    if not am.strict_equal(r['algorithm'], expected):
        raise ValueError('OPEN algorithm metadata/factors mismatch')
    if (not am.strict_equal(p['target'], obj['target']) or
            not am.strict_equal([p['target_generation'], p['target_description_id']], [1, 27])):
        raise ValueError('OPEN immutable target mismatch')
    _, compiled_raw = am.snapshot(candidate.parent, {'file': 'compile-receipt.json',
                                                    'sha256': p['execution']['compile_receipt_sha256']})
    compiled = parse_json(compiled_raw)
    frontend = p['execution']['frontend']['sources']
    if set(frontend) != set(prov.FRONTEND_INPUTS) or set(compiled['sources']) != set(prov.COMPILE_INPUTS):
        raise ValueError('incomplete or unexpected renderer source file sets')
    expected_sources = dict(frontend)
    for rel, digest in compiled['sources'].items():
        if rel in expected_sources and expected_sources[rel] != digest:
            raise ValueError('conflicting recorded renderer source hashes')
        expected_sources[rel] = digest
    snapshot_sources = parse_json(read_bounded(renderer_root / 'SOURCES.json', 4 * 1024 * 1024))
    if not am.strict_equal(snapshot_sources, expected_sources):
        raise ValueError('archived source map differs from recorded closure')
    for rel, digest in expected_sources.items():
        path = (renderer_root / rel).resolve(strict=True)
        if not path.is_relative_to(renderer_root) or sha(path) != digest:
            raise ValueError('archived renderer source mismatch: ' + rel)
    # Unmodified archived verifier: no historical frontend hash is overwritten.
    prov.validate_record(p['execution'], compiled)
    _, control = am.snapshot(candidate.parent, {'file': 'control.txt', 'sha256': p['control_sha256']})
    if p['protocol'] != 'DVH3' or control != open_dm.control(obj, meta, variant).encode():
        raise ValueError('OPEN native protocol mismatch')
    for name in ('stdout', 'stderr'):
        am.snapshot(candidate.parent, {'file': 'native.' + name, 'sha256': p[name + '_sha256']})
    pixels = am.output_snapshot(candidate.parent, r['output'], obj['frame']['width'], obj['frame']['height'])
    pa = am.pixel_samples(pixels)
    del pixels
    ref_raw = read_bounded(reference, 4 * 1024 * 1024)
    b, pb = result_manifest(reference, ref_raw)
    if b['schema'] != 3 or b['role'] != 'reference' or not am.strict_equal(r['source_alignment'], b['alignment']):
        raise ValueError('strict same-source retained reference required')
    if p['input_manifest']['sha256'] != b['provenance']['input_manifest']['sha256']:
        raise ValueError('candidate/reference input manifest mismatch')
    report = {'schema': 'hdr.open-dm-recorded-comparison.v1', 'algorithm': r['algorithm'],
              'source_alignment': r['source_alignment'], 'encoding': ENCODING,
              'candidate_sha256': r['output']['sha256'], 'reference_sha256': b['output']['sha256'],
              'candidate_manifest_sha256': hashlib.sha256(raw).hexdigest(),
              'reference_manifest_sha256': hashlib.sha256(ref_raw).hexdigest(),
              'renderer_sources': expected_sources, 'recorded_renderer_frontend': p['execution']['frontend'],
              'recorded_compile_receipt_sha256': p['execution']['compile_receipt_sha256'],
              'comparator': {'entry_point': 'recorded_open_compare.compare_recorded',
                             'driver_sha256': sha(__file__), 'archived_frontend': prov.implementation(),
                             'canonicalization': 'json.loads(json.dumps(expected_algorithm, allow_nan=False)); strict_equal unchanged',
                             'metric_source_sha256': sha(renderer_root / 'tools/dolby_harness/metric.py'),
                             'python_version': sys.version, 'python_sha256': sha(Path(sys.executable).resolve())},
              'metric': 'ITU-R BT.2124-0 Annex 1 deltaE_ITP',
              'statistics': compare_pixels(pa, pb),
              'scope': 'corrected comparison of immutable old execution; NOT old open_dm.compare success, new render, or full Dolby/OEM/optical acceptance'}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renderer-root', required=True)
    parser.add_argument('candidate')
    parser.add_argument('reference')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    output = Path(args.report)
    if output.exists():
        raise ValueError('never overwrite an existing comparison')
    report = compare_recorded(args.renderer_root, args.candidate, args.reference)
    with output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'statistics': report['statistics'], 'report_sha256': sha(output)}), flush=True)


if __name__ == '__main__':
    main()
