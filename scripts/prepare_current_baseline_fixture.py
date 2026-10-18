#!/usr/bin/env python3
"""POST-REVIEW ONLY: once-only genuinely invalidated current baseline fixture.

Coordinator2541 adjudication requires current positive/deep-tamper coverage of
this still-supported schema3 stock baseline. This is NOT another mapping curve,
new vendor acquisition, accuracy comparison, or relabelled historical execution.
Run with the reviewed whole-candidate qualification batch, never integration.
"""
import argparse
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.dolby_harness import authored_master as am, harness, provenance
from tools.dolby_harness.contracts import alignment, input_manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'native', 'compile-receipt', 'reference-exr', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('native x86_64 Linux only')
    output = a.output.resolve()
    if any(output == Path(t) or output.is_relative_to(t) for t in ('/tmp', '/private/tmp', '/var/tmp', '/private/var/tmp')):
        raise ValueError('new durable task-owned output required')
    output.mkdir(parents=True, exist_ok=False)
    obj, _, meta = input_manifest(a.input)
    if obj['schema'] != 3 or obj['frame']['index'] != 256 or obj['target']['id'] != '27':
        raise ValueError('exact retained original256/target27 current-parser fixture required')
    raw = a.input.read_bytes()
    plan = {'schema': 'hdr.current-baseline-fixture-plan.v1',
            'input_sha256': provenance.sha_bytes(raw),
            'recipe_sha256': provenance.sha(__file__),
            'frontend': provenance.implementation(), 'native_sha256': provenance.sha(a.native),
            'compile_receipt_sha256': provenance.sha(a.compile_receipt),
            'reference_exr_sha256': provenance.sha(a.reference_exr),
            'source_alignment': alignment(obj, meta),
            'scope': 'genuinely invalidated supported baseline test fixture; no official/accuracy comparison',
            'maximum_native_baseline_renders': 1, 'vendor_calls': 0, 'metric_runs': 0}
    # Bind the genuine source/target/reference log/receipt BEFORE any fixture render.
    am.reference_provenance(a.input.parent, obj['metadata']['declaration_repair'], obj, meta,
                            {'file': str(a.reference_exr.resolve()), 'sha256': provenance.sha(a.reference_exr)})
    (output / 'PLAN.json').write_text(json.dumps(plan, indent=2) + '\n')
    reference = am.normalize_reference(a.input, a.reference_exr, output / 'reference')
    candidate = harness.render(a.input, a.native, output / 'candidate', a.compile_receipt)
    receipt = {'schema': 'hdr.current-baseline-fixture.v1',
               'plan_sha256': provenance.sha(output / 'PLAN.json'),
               'candidate': {'path': str(candidate), 'sha256': provenance.sha(candidate)},
               'reference': {'path': str(reference), 'sha256': provenance.sha(reference)},
               'baseline_renders': 1, 'vendor_calls': 0, 'metric_runs': 0,
               'environment_additions': {'HDR_AUTHORED_CURRENT_BASELINE_CANDIDATE': str(candidate),
                                         'HDR_AUTHORED_CURRENT_BASELINE_REFERENCE': str(reference)}}
    (output / 'BASELINE-FIXTURE.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(output / 'BASELINE-FIXTURE.json')


if __name__ == '__main__':
    main()
