"""Deferred sqrt-sum math/transport regressions; no invented vendor fixtures."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dolby_harness import sqrtsum as sq, open_dm as dm
from tools.dolby_harness import authored_master as am
from tools.dolby_harness.contracts import input_manifest


class SqrtSumMathTests(unittest.TestCase):
    def setUp(self):
        # Mathematical control coordinates only, never sent to vendor tools.
        self.curve = sq.prepare((.0196536, .272, .853468), .005, 4000, 0, 600)

    def test_positive_anchor_closure_and_neighbours(self):
        c = self.curve
        self.assertAlmostEqual(c['weight'], 1.8858359319351408, places=12)
        for q, y in zip(c['source_anchors'], c['target_anchors']):
            self.assertAlmostEqual(sq.curve_eval(q,c), y, places=13)
            for v in (math.nextafter(q,0), math.nextafter(q,1)):
                self.assertTrue(0 <= sq.curve_eval(v,c) <= 1)
        self.assertEqual(sq.curve_eval(0,c),c['target_anchors'][0])
        self.assertEqual(sq.curve_eval(1,c),c['target_anchors'][2])
        self.assertEqual(c,json.loads(json.dumps(c,allow_nan=False)))

    def test_original_display_bounds_and_invalid_metadata(self):
        self.assertNotEqual(self.curve,sq.prepare((.0196536,.272,.853468),.005,2000,0,600))
        for anchors in ((0,0,.9),(0,.9,.9),(.2,.1,.9),(0,float('nan'),1)):
            with self.assertRaises(ValueError): sq.prepare(anchors,.005,4000,0,600)
        for bounds in ((1,1,0,600),(.005,float('nan'),0,600),(.005,4000,600,600)):
            with self.assertRaises(ValueError): sq.prepare((0,.3,.9),*bounds)

    def test_zero_y_and_actual_nonzero_sg(self):
        c=self.curve;sop=(1.005006,-.002006,2000/2007)
        self.assertEqual(sq.evaluate((0,0,0),c,sop,(-.0105,-.002)),(0,0,0))
        a=sq.evaluate((1,2,3),c,sop,(-.0105,-.002))
        b=sq.evaluate((1,2,3),c,sop,(-.0105,0))
        self.assertNotEqual(a,b)
        self.assertEqual(b,sq.evaluate((1,2,3),c,sop,(.5,0)))
        for rgb in ((-1,2,3),(float('nan'),2,3),(10001,2,3)):
            with self.assertRaises(ValueError): sq.evaluate(rgb,c,sop,(0,0))
        with self.assertRaises(ValueError): sq.evaluate((10000,)*3,c,(1.5,.5,1),(0,0))

    def test_gpu_download_receipt_failclosed(self):
        obj={'frame':{'width':2,'height':1},'target':{'id':'27'}}
        config={'protocol':'DVH4','target_description_id':27,'RGBA_components':4,
            'independent_alpha':True,'background':'skip','background_transparency':1,
            'blend':False,'tiles':False,'hooks':0,'lut':False,'distortion':False}
        domain={'schema':'hdr.sqrtsum.gpu-domain.v1','population':2,'valid':2,'invalid':0,
                'channel':'downloaded-RGBA-alpha-exact1'}
        encode=lambda c,d: ('native device\n'+json.dumps(c)+'\n'+json.dumps(d)+'\n').encode()
        self.assertEqual(dm.sqrtsum_gpu_domain(encode(config,domain),obj),domain)
        for field,value in (('invalid',1),('valid',1),('population',1),('valid',True)):
            bad=copy.deepcopy(domain);bad[field]=value
            with self.assertRaises(ValueError):dm.sqrtsum_gpu_domain(encode(config,bad),obj)
        bad=copy.deepcopy(config);bad['background']='color'
        with self.assertRaises(ValueError):dm.sqrtsum_gpu_domain(encode(bad,domain),obj)


class SqrtSumAuthenticTests(unittest.TestCase):
    def test_real_original_target_protocol_and_nonzero_sg(self):
        # Explicit retained manifests ONLY; no acquisition or renderer invocation.
        for variable,shot in (('HDR_AUTHORED_INPUT',256),('HDR_AUTHORED_INPUT714',714)):
            obj,_,meta=input_manifest(Path(os.environ[variable]))
            self.assertEqual(obj['frame']['index'],shot)
            a=dm.algorithm(obj,meta,dm.SQRTSUM_VARIANT)
            self.assertTrue(am.strict_equal(a,json.loads(json.dumps(a,allow_nan=False))))
            self.assertEqual(a['id'],sq.ALGORITHM)
            self.assertEqual(a['prepared_curve']['source_display_nits'],[.005,4000])
            self.assertEqual(a['unapplied_trim_indexes'],[0,1,2,8])
            self.assertEqual(a['unapplied_trim_values']['8'],'-0.75')
            if shot==714:self.assertNotEqual(a['color_factors']['sg'],0)
            tokens=dm.control(obj,meta,dm.SQRTSUM_VARIANT).split()
            self.assertEqual(tokens[:5],['DVH4','4096','2160','1','27'])
            self.assertEqual(len(tokens),34)
            self.assertEqual(tokens[28],'7')
            self.assertEqual(a['source_records'],meta['records'])
            self.assertFalse(a['full_mapping_complete'])


if __name__=='__main__':unittest.main()
