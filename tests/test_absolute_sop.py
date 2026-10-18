"""Deferred ABI364 regressions; actual retained authentic frame256 only.

No render/vendor/metric invocation. Old outputs keep old source identities.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import authored_master as am
from tools.dolby_harness import open_dm as dm
from tools.dolby_harness import open_dm_provenance as prov
from tools.dolby_harness.contracts import input_manifest


class AbsoluteAuthenticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obj, _, cls.meta = input_manifest(Path(os.environ['HDR_AUTHORED_INPUT']))
        if cls.obj['frame']['index'] != 256:
            raise AssertionError('authentic retained256 required')

    def test_explicit_absolute_algorithm_domain_and_original_association(self):
        saved = copy.deepcopy(self.meta)
        a = dm.algorithm(self.obj, self.meta, dm.ABSOLUTE_VARIANT)
        old = dm.algorithm(self.obj, self.meta, 'l1-hermite-sop')
        self.assertEqual(a['id'], 'open-xml205-hermite-absolute-pq-sop-v1')
        self.assertEqual(a['sop_domain'], 'PL_DOVI_DM_SOP_ABSOLUTE_PQ')
        self.assertIn('no target normalization', a['domain'])
        self.assertIn('not normative', a['sop_clamp_policy'])
        for key in ('l1', 'target', 'source_records', 'selected_records', 'original_trim',
                    'derived_factors', 'applied_factors', 'unapplied_trim_values'):
            self.assertEqual(a[key], old[key])
        self.assertEqual(a['derived_factors']['exact'], {'S':'507/500','O':'-7/500','P':'2000/2001'})
        self.assertEqual(a['unapplied_trim_values']['6'], '-0.002')
        self.assertEqual(a['unapplied_trim_values']['8'], '-0.75')
        self.assertIsNone(a['selected_cm_name'])
        self.assertEqual(a['applied_stages'], ['explicit presence-aware L1',
            'existing L1 chroma compensation once', 'OPEN absolute-PQ SOP',
            'existing final physical gamut mapping once'])
        self.assertEqual(self.meta, saved)
        # Exact algorithm records of old variants remain unchanged. This reads
        # their retained manifests only, not pixels or old frontend execution.
        prior = json.loads(Path(os.environ['HDR_OPEN_PRIOR_RESULTS']).read_bytes())
        self.assertEqual(set(prior), set(dm.VARIANTS[:3]))
        for variant, path in prior.items():
            historical = json.loads(Path(path).read_bytes())
            self.assertTrue(am.strict_equal(historical['algorithm'],
                                           dm.algorithm(self.obj, self.meta, variant)))

    def test_native_variant3_explicit_acceptance_and_no_fallback(self):
        values = dm.control(self.obj, self.meta, dm.ABSOLUTE_VARIANT).split()
        self.assertEqual(values[27], '3')
        old = dm.control(self.obj, self.meta, 'l1-hermite-sop').split()
        self.assertEqual(values[:27] + values[28:], old[:27] + old[28:])
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            root = Path(tmp)
            for variant, accepted in (('3', True), ('4', False), ('-1', False), ('0', False), ('1', False)):
                tokens = values[:]; tokens[27] = variant
                (root/'control').write_text(' '.join(tokens)+'\n')
                p = subprocess.run([os.environ['HDR_OPEN_NATIVE'],str(root/'control'),
                    str(root/'absent-input'),str(root/'absent-output')],
                    env=prov.native_environment(root),capture_output=True,timeout=30)
                self.assertEqual(p.returncode, 1 if accepted else 2)
                self.assertIn(b'No successful OPEN' if accepted else b'Invalid DVH3',p.stderr)
                self.assertEqual(p.stdout,b'')
                self.assertFalse((root/'absent-output').exists())

    def test_absolute_result_rejects_domain_algorithm_and_old_abi(self):
        # Current-head genuine independent result supplies a runnable negative
        # control. Historical ABI364 positives remain bound to their old head;
        # do not rerender or relabel them to satisfy this new regression.
        paths = json.loads(Path(os.environ['HDR_OPEN_RESULTS']).read_bytes())
        path = Path(paths[dm.SQRTSUM_VARIANT])
        actual = json.loads(path.read_bytes())
        for key, value in (('id',dm.ALGORITHM), ('sop_domain','PL_DOVI_DM_SOP_TARGET_NORMALIZED_PQ'),
                           ('domain','target-normalized PQ'), ('variant','l1-hermite-sop')):
            bad = copy.deepcopy(actual); bad['algorithm'][key] = value
            with self.assertRaises(ValueError):dm.validate_result(path,json.dumps(bad).encode())
        compiled = copy.deepcopy(actual['provenance']['execution']['compile_receipt'])
        compiled['abi'] = 362
        with self.assertRaisesRegex(ValueError,'ABI368'):prov.validate_compile(compiled)


if __name__ == '__main__':unittest.main()
