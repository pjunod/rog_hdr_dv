"""Deferred public mathematical regressions, not authored metadata fixtures.

No vendor invocation or source/reference fabrication. Execute only in the
completed candidate's single post-review affected batch.
"""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import public_mapping as pm


class PublicMappingMathTests(unittest.TestCase):
    def test_rational_anchor_solution_poles_and_singularities(self):
        xs, ys = (0, 10, 1000), (0, 8, 100)
        c = pm.rational_prepare(xs, ys)
        for x, y in zip(xs, ys):
            self.assertAlmostEqual(pm.rational_eval(c, x), y, places=10)
        for bad in ((0, 0, 1000), (0, 1001, 1000), (0, math.nan, 1000)):
            with self.assertRaises(ValueError):
                pm.rational_prepare(bad, ys)
        with self.assertRaises(ValueError):
            pm.rational_eval((0, 1, -.001), 1000)

    def test_color_zero_limits_and_nonzero_chroma_neutral_sg_bypass(self):
        self.assertEqual(pm.color_transform((0, 0, 0), pm.BT2020_WEIGHTS, -.5, -.5), (0, 0, 0))
        rgb = (0, 1, 2)
        for cw in (-.5, .5):
            self.assertEqual(pm.color_transform(rgb, pm.BT2020_WEIGHTS, cw, 0), rgb)
            result = pm.color_transform(rgb, pm.BT2020_WEIGHTS, cw, -.5)
            self.assertEqual(result[0], 0)
            self.assertTrue(all(math.isfinite(x) for x in result))
        with self.assertRaises(ValueError):
            pm.color_transform(rgb, pm.BT2020_WEIGHTS, 1, 0)

    def test_linear_basis_matrix_and_declared_black_floor_separation(self):
        p3 = ((.68, .32), (.265, .69), (.15, .06), (.3127, .329))
        bt = ((.708, .292), (.17, .797), (.131, .046), (.3127, .329))
        to_bt, to_p3 = pm.convert_matrix(p3, bt), pm.convert_matrix(bt, p3)
        for rgb in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)):
            result = pm.apply_matrix(to_p3, pm.apply_matrix(to_bt, rgb))
            for x, y in zip(rgb, result):
                self.assertAlmostEqual(x, y, places=12)
        curve = pm.baker_prepare((0, .3, .9), 0, 600)
        self.assertEqual(curve['declared_black'], 0)
        self.assertEqual(curve['effective_black'], .00001)

    def test_scene_anchor_knee_and_curve_identity_does_not_skip_sop(self):
        curve = pm.mpc_prepare((0, .3, .9), 600)
        self.assertEqual(curve['source_anchors'][0], 0)
        rgb = (1, 1, 1)
        identity = pm.mpc_prepare((0, .2, .3), 1000)
        self.assertTrue(identity['identity'])
        result = pm.mpc(rgb, identity, (1, -.01, 1), (0, 0))
        self.assertTrue(all(0 <= x < 1 for x in result))
        pre = pm.mpc(rgb, curve, (1, -.01, 1), (0, 0))
        post = pm.mpc_post(rgb, curve, (1, -.01, 1), (0, 0))
        self.assertNotEqual(pre, post)


if __name__ == '__main__':
    unittest.main()
