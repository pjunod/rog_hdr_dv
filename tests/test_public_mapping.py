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
    def test_mastblack_zero_low_knee_and_declared_anchor(self):
        l1 = (.0196536, .272, .853468)
        c = pm.mpc_mastblack_prepare(l1, 600, .005)
        self.assertEqual(c, pm.mpc_mastblack_prepare((0, *l1[1:]), 600, .005))
        self.assertEqual(c['source_anchors'][0], .005)
        for x, y in zip(c['source_anchors'], c['mapped_anchors']):
            self.assertAlmostEqual(pm.rational_eval(c['coefficients'], x), y, places=9)
        for black in (math.nan, math.inf, -1, 100):
            with self.assertRaises(ValueError):
                pm.mpc_mastblack_prepare(l1, 600, black)
        self.assertTrue(pm.mpc_mastblack_prepare(l1, 10000, .005)['identity'])

    def test_mastblack_color_after_ratio_not_sg_drop(self):
        c = pm.mpc_mastblack_prepare((.0196536, .272, .853468), 600, .005)
        rgb, sop = (1, 2, 3), (1.005006, -.002006, 2000/2007)
        base = pm.mpc_pre_y(rgb, c, sop, (0, 0))
        expected = pm.color_transform(tuple(pm.pq_inverse(v) for v in base),
                                      pm.BT2020_WEIGHTS, -.0105, -.002)
        actual = pm.mpc_pre_y_mastblack(rgb, c, sop, (-.0105, -.002))
        for x, q in zip(actual, expected):
            self.assertAlmostEqual(x, pm.pq_eotf(q), places=12)
        self.assertNotEqual(actual, base)
        self.assertEqual(pm.mpc_pre_y_mastblack((0, 0, 0), c, sop, (-.01, -.002)), (0, 0, 0))
        self.assertEqual(pm.mpc_pre_y_mastblack(rgb, c, sop, (-.5, 0)),
                         pm.mpc_pre_y_mastblack(rgb, c, sop, (.5, 0)))
        with self.assertRaises(ValueError):
            pm.mpc_pre_y_mastblack((10000,)*3, c, sop, (0, 0))
        with self.assertRaises(ValueError):
            pm.mpc_pre_y_mastblack((10000,)*3, {'identity': True}, (1, 0, 1), (.5, .5))

    def test_two_named_xml_conventions_neutral_limits_and_exact_composition(self):
        for name in ('xml-wire-continuous-v1', 'xml-direct-lgg-hypothesis-v1'):
            neutral = pm.xml_lgg_coefficients(['0'] * 5, name)
            self.assertEqual(neutral['sop'], (1, 0, 1))
            self.assertEqual(neutral['color'], (0, 0))
            self.assertFalse(neutral['direct_XML_pixel_semantics_proven'])
        controls = ('-0.028', '0', '0.001', '-0.002', '0')
        wire = pm.xml_lgg_coefficients(controls, 'xml-wire-continuous-v1')
        direct = pm.xml_lgg_coefficients(controls, 'xml-direct-lgg-hypothesis-v1')
        self.assertEqual(wire['sop'], (1.014, -.014, 2000/2001))
        self.assertEqual(direct['sop'], (1.028, -.028, 1000/1001))
        self.assertEqual(wire['color'], (-.001, 0))
        self.assertEqual(direct['color'], (-.002, 0))
        for controls, name in ((['0'] * 5, 'fitted-alpha'),
                               (('0', '0', '-1', '0', '0'), 'xml-direct-lgg-hypothesis-v1'),
                               (('0', '0', 'NaN', '0', '0'), 'xml-wire-continuous-v1')):
            with self.assertRaises(ValueError):
                pm.xml_lgg_coefficients(controls, name)

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

    def test_coupled_matrix_inverse_and_explicit_domain_rejection(self):
        forward = ((1, .1, 0), (0, 1, .1), (.1, 0, 1))
        inverse = pm.inverse_matrix(forward)
        for rgb in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            got = pm.apply_matrix(inverse, pm.apply_matrix(forward, rgb))
            for a, b in zip(got, rgb):
                self.assertAlmostEqual(a, b, places=12)
        with self.assertRaises(ValueError):
            pm.inverse_matrix(((1, 1, 1),) * 3)
        for rgb, color in (((-1, 0, 0), (0, 0)), ((1, 1, 1), (0, .1))):
            with self.assertRaises(ValueError):
                pm.mpc_pre_ipt(rgb, {'identity': True}, (1, 0, 1), color, {})

    def test_normalized_scalar_post_curve_has_no_mpc_floor_or_rgb_sop(self):
        curve = {'identity': True, 'peak': 600}
        sop = (1, -.1, 1)
        counts = {}
        self.assertEqual(pm.mpc_post_normalized_y((0, 0, 0), curve, sop, (-.001, 0)), (0, 0, 0))
        self.assertEqual(pm.mpc_post_normalized_y((.001, .001, .001), curve, sop, (-.001, 0), counts), (0, 0, 0))
        self.assertEqual(counts['affine_negative'], 1)
        rgb = (1, 2, 3)
        result = pm.mpc_post_normalized_y(rgb, curve, (1, -.01, 1), (-.001, 0))
        self.assertAlmostEqual(result[0]/rgb[0], result[1]/rgb[1], places=12)
        self.assertAlmostEqual(result[1]/rgb[1], result[2]/rgb[2], places=12)
        for invalid in ((math.nan, 1, 1), (-1, 1, 1)):
            with self.assertRaises(ValueError):
                pm.mpc_post_normalized_y(invalid, curve, sop, (-.001, 0))
        with self.assertRaises(ValueError):
            pm.mpc_post_normalized_y(rgb, curve, sop, (-.001, .1))
        with self.assertRaises(ValueError):
            pm.mpc_post_normalized_y(rgb, curve, (1, math.inf, 1), (-.001, 0))


if __name__ == '__main__':
    unittest.main()
