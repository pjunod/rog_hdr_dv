"""Hash/receipt-only closeout; no evaluator imports or metric/image execution."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2].parent
OUT = ROOT / 'sol-curve370'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    frozen = load(OUT / 'FROZEN.json')
    results = load(OUT / 'RESULTS.json')
    assert results['frozen_sha256'] == sha(OUT / 'FROZEN.json')
    sources = dict(frozen['repository_import_closure_sha256'])
    sources.update(frozen['retained_source_hashes'])
    for rel, digest in sources.items():
        assert sha(ROOT / rel) == digest, rel
    assert frozen['preflight_sha256'] == sha(ROOT / 'scratch370/source-curve-preflight.json')
    for shot, receipt in results['shots'].items():
        provenance = frozen['shots'][shot]
        for key in ('input', 'metadata_driver', 'reference_manifest'):
            assert sha(provenance[key+'_path']) == provenance[key+'_sha256']
        result_path = OUT / shot / 'RESULT.json'
        output_path = OUT / shot / 'lattice-output.json'
        assert sha(result_path) == receipt['result_sha256']
        assert sha(output_path) == receipt['lattice_output_sha256']
        detail, outputs = load(result_path), load(output_path)
        started = load(OUT / shot / 'STARTED.json')
        assert started['candidate_executions_authorized'] == receipt['candidate_executions'] == 1
        assert started['frozen_sha256'] == sha(OUT / 'FROZEN.json')
        assert detail['population'] == detail['valid'] == receipt['population'] == receipt['valid'] == 34560
        assert detail['invalid'] == receipt['invalid'] == {}
        assert len(outputs) == detail['population']
        assert [tuple(r['xy']) for r in outputs] == [(x, y) for y in range(0, 2160, 16)
                                                    for x in range(0, 4096, 16)]
        assert all('invalid' not in r and 'final_BT2020_nits' in r for r in outputs)
        assert detail['primary_all_population'] == receipt['primary_all_population']
        assert detail['counters'] == receipt['counters']
        assert detail['execution_counts'] == dict(chain_calls=34560, actual_colour_calls=34560,
                                                  final_P3_clip_calls=34560)
        assert provenance['preparation_proof']['preflight_preparation_exact_match']
        # Stored receipt consistency only; no errors or image metrics recalculated.
        for name in ('raw_strata', 'final_clip_strata'):
            bins = detail[name]
            assert sum(v['pixels'] for k, v in bins.items() if k.startswith('refY<')) == 34560
            assert sum(v['pixels'] for k, v in bins.items()
                       if k.startswith('original/') and k.count('/') == 1) == 34560
        assert sum(v['pixels'] for v in detail['final_clip_by_source_Y_halfdecade'].values()) == 34560
        assert detail['pass_mean1_p953_sampled_only'] == receipt['pass_mean1_p953_sampled_only'] is True
        assert receipt['disposition'] == 'REPORT_TO_COORDINATOR_NO_PROMOTION'
    # Static parse only. py_compile was also run before the candidate execution.
    for path in HERE.glob('sol_curve370_*.py'):
        ast.parse(path.read_text(), filename=str(path))
    tracked = subprocess.run(['git', '-C', str(ROOT / 'repo'), 'diff', '--exit-code'],
                             check=True, capture_output=True, text=True)
    staged = subprocess.run(['git', '-C', str(ROOT / 'repo'), 'diff', '--cached', '--exit-code'],
                            check=True, capture_output=True, text=True)
    head = subprocess.run(['git', '-C', str(ROOT / 'repo'), 'rev-parse', 'HEAD'],
                          check=True, capture_output=True, text=True).stdout.strip()
    # Own compilation intermediates only; evidence lives in manifest/receipts.
    syntax = OUT / 'syntax'
    if syntax.exists():
        shutil.rmtree(syntax)
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'MANIFEST.json')
    paths += sorted(HERE.glob('sol_curve370_*'))
    artifact_hashes = {str(p.relative_to(ROOT)): dict(sha256=sha(p), bytes=p.stat().st_size)
                       for p in paths if p.is_file()}
    manifest = dict(schema='hdr.sol370.artifact-manifest.v1', task='t_871482d9',
        verification='PASS hash identities, full stored-output population, once-only receipts, strata accounting; '
                     'no candidate/preflight/baseline/metric reexecution',
        candidate_executions={'256': 1, '714': 1}, unit_batches=0,
        preflight_executions=0, baseline_executions=0, native_requests=0, holdout_access=False,
        preexecution_python_syntax_compile=True, final_source_AST_parse=True,
        tracked_worktree_diff_empty=not tracked.stdout, staged_diff_empty=not staged.stdout,
        repository_head=head, artifacts=artifact_hashes,
        disposition='REPORT_TO_COORDINATOR_NO_PROMOTION')
    with (OUT / 'MANIFEST.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print('VERIFIED', len(artifact_hashes), 'artifacts; manifest_sha256', sha(OUT / 'MANIFEST.json'))


if __name__ == '__main__':
    main()
