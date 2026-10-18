"""One fixed native Eq5/PQ(Y)/MB hybrid; no fitting, renderer or acceptance.

The source specifies IPT intensity; PQ(Y) embedding, edge replication, below-PQ0
projection and achromatic Y0 are explicit finite implementation conventions.
Y0 is NOT claimed to be the continuous limit of direction-dependent RGB*Map/Y.
Prepare/compile/freeze first, then execute once per authorized development shot.
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

R = Path('/work/hdr-nativehdr10-20261011/t_bb5b2ce0')
OUT = Path('/work/hdr-nativehdr10-20261011/t_77559dbf/gaussian357')
FRONT = R / 'mastblack347/render-frontend355'
sys.dont_write_bytecode = True
sys.path.insert(0, str(FRONT))
from tools.dolby_harness import public_mapping as pm, open_dm
from tools.dolby_harness.contracts import alignment, input_manifest
from tools.dolby_harness.metric import delta_itp, pq_eotf, pq_inverse, rgb_to_itp, summarize

P3 = ((.68,.32),(.265,.69),(.15,.06),(.3127,.329))
BT = ((.708,.292),(.17,.797),(.131,.046),(.3127,.329))
M = pm.convert_matrix(P3, BT)
TO_P3 = pm.convert_matrix(BT, P3)
FILES = {256: ('input366-343/input.json', 'sample-cache336.json'),
         714: ('frame714-346/input.json', 'frame714-346/sample-cache714-346.json')}
BASELINES = {256: (1.123974, 2.719644), 714: (2.418842, 5.553420)}


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def save(p, d):
    with p.open('x') as f:
        f.write(json.dumps(d, indent=2, allow_nan=False) + '\n')


def verify_front():
    sources = json.loads((FRONT / 'SOURCES.json').read_text())
    for rel, digest in sources.items():
        assert sha(FRONT / rel) == digest, rel
    return sources


def prepare():
    sources = verify_front()
    records = {}
    for shot, (mf, cf) in FILES.items():
        manifest, cache = R / mf, R / cf
        obj, src, meta = input_manifest(manifest)
        assert obj['frame']['index'] == shot
        assert (obj['frame']['width'], obj['frame']['height']) == (4096,2160)
        assert obj['target']['id'] == '27' and obj['target']['max_nits'] == 600
        assert obj['source']['mastering']['min_nits'] == .005
        assert obj['source']['primaries'] == 'p3d65' and obj['source']['transfer'] == 'pq'
        assert obj['source']['range'] == 'full' and obj['source']['layout'] == 'c3-f32le'
        refmanifest = R / f'mastblack347/{shot}/reference-rebound355.json'
        ref = json.loads(refmanifest.read_text())
        assert ref['role'] == 'reference' and ref['schema'] == 3
        assert ref['alignment'] == alignment(obj, meta)
        assert ref['provenance']['input_manifest']['sha256'] == sha(manifest)
        refpath = Path(ref['output']['file'])
        assert sha(src) == obj['frame']['input']['sha256']
        assert sha(refpath) == ref['output']['sha256']
        assert Path(src).stat().st_size == refpath.stat().st_size == 4096*2160*12
        old = json.loads((R / f'mastblack347/{shot}/lattice.json').read_text())
        assert sha(cache) == old['cache_sha256']
        a = open_dm.algorithm(obj, meta, open_dm.MB_VARIANT)
        curve = pm.mpc_mastblack_prepare(tuple(meta['l1'][k] for k in ('min_pq','avg_pq','max_pq')),600,.005)
        assert curve == a['prepared_curve']
        assert not curve['identity']
        sop = [a['applied_factors'][k] for k in ('S','O','P')]
        color = [a['color_factors'][k] for k in ('cw','sg')]
        if shot == 714:
            assert color[1] != 0
        control = OUT / f'{shot}.control'
        with control.open('x') as f:
            f.write(' '.join(map(repr, [v for row in M for v in row] + sop + list(curve['coefficients']))) + '\n')
        records[str(shot)] = {'manifest': str(manifest), 'manifest_sha256': sha(manifest),
            'source': str(src), 'source_sha256': sha(src),
            'reference_manifest': str(refmanifest), 'reference_manifest_sha256': sha(refmanifest),
            'reference': str(refpath), 'reference_sha256': sha(refpath),
            'cache': str(cache), 'cache_sha256': sha(cache), 'metadata': meta,
            'algorithm_metadata': a, 'SOP': sop, 'CW_SG': color, 'curve': curve,
            'control': str(control), 'control_sha256': sha(control), 'p3_to_bt2020': M}
    cmd = ['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror',
           str(OUT/'sol_gaussian357_scalar.c'),'-lm','-o',str(OUT/'scalar')]
    p = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ,TMPDIR=str(OUT)))
    save(OUT/'COMPILE.json', {'argv': cmd, 'exit': p.returncode, 'stdout':p.stdout,'stderr':p.stderr})
    assert p.returncode == 0, p.stderr
    receipt = {'schema':'hdr.sol.gaussian357.freeze.v1','shots':records,'frontend_sources':sources,
        'frontend_map_sha256':sha(FRONT/'SOURCES.json'),
        'script_sha256':sha(__file__),'scalar_source_sha256':sha(OUT/'sol_gaussian357_scalar.c'),
        'binary_sha256':sha(OUT/'scalar'),'compile_sha256':sha(OUT/'COMPILE.json'),
        'contract_sha256':sha(OUT/'sol_gaussian357_contract.txt'),
        'pixel_executions':0,'units':0,'holdout_access':False}
    save(OUT/'FROZEN.json', receipt)
    print('FROZEN', sha(OUT/'FROZEN.json'), json.dumps({k:v for k,v in receipt.items() if k!='shots' and k!='frontend_sources'}), flush=True)


def signed_stats(vals):
    if not vals:
        return None
    vals = sorted(vals)
    return {'pixels':len(vals),'mean':math.fsum(vals)/len(vals),'min':vals[0],
            'p05':vals[math.ceil(.05*len(vals))-1],'p50':vals[math.ceil(.5*len(vals))-1],
            'p95':vals[math.ceil(.95*len(vals))-1],'max':vals[-1],
            'mean_abs':math.fsum(abs(v) for v in vals)/len(vals),
            'negative':sum(v<0 for v in vals),'zero':sum(v==0 for v in vals),
            'positive':sum(v>0 for v in vals),'percentile':'nearest-rank'}


def metric_stats(rows):
    return {**summarize(v[0] for v in rows),
        'mean_signed720ITP':[math.fsum(v[1][i] for v in rows)/len(rows) for i in range(3)]} if rows else None


def execute(shot):
    frozen = json.loads((OUT/'FROZEN.json').read_text()); d = frozen['shots'][str(shot)]
    assert sha(__file__) == frozen['script_sha256']
    assert sha(OUT/'scalar') == frozen['binary_sha256']
    assert sha(OUT/'sol_gaussian357_scalar.c') == frozen['scalar_source_sha256']
    assert sha(OUT/'sol_gaussian357_contract.txt') == frozen['contract_sha256']
    verify_front()
    for pathkey, hashkey in (('source','source_sha256'),('reference','reference_sha256'),
                            ('cache','cache_sha256'),('control','control_sha256')):
        assert sha(d[pathkey]) == d[hashkey]
    stage = OUT / str(shot); stage.mkdir(exist_ok=False)
    # The directory is a once-only marker: failed execution must NOT be retried.
    start = time.time()
    cmd = [str(OUT/'scalar'),d['control'],d['source'],str(stage/'lattice-fields.f64')]
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=700)
    save(stage/'EXECUTION.json',{'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.time()-start})
    assert p.returncode == 0, p.stderr
    full = json.loads(p.stdout)
    cache = json.loads(Path(d['cache']).read_text())
    fields = list(struct.iter_unpack('<8d',(stage/'lattice-fields.f64').read_bytes()))
    coords = [(x,y) for y in range(0,2160,16) for x in range(0,4096,16)]
    assert len(cache) == len(fields) == len(coords) == 34560
    assert [tuple(v[0]) for v in cache] == coords
    counters = collections.Counter(); invalid = collections.Counter()
    bins = collections.defaultdict(list); shifts = collections.defaultdict(list)
    rawshifts = collections.defaultdict(list); errors = []; raw_errors=[]; rows=[]
    max_source_disagreement=0.
    ranges = {k:[math.inf,-math.inf] for k in ('restored_RGB_nits','postcolor_PQ','physical_P3_nits','encoded_PQ')}
    def observe(key, values):
        ranges[key][0]=min(ranges[key][0],min(values))
        ranges[key][1]=max(ranges[key][1],max(values))
    with Path(d['reference']).open('rb') as refstream:
        for xy, entry, values in zip(coords,cache,fields):
            _, srcpq, srclin, ref, itp, ry, spread, vol = entry
            linear, Y, io, im, raw_is, is_ = values[:3], *values[3:]
            max_source_disagreement=max(max_source_disagreement,max(abs(x-y) for x,y in zip(linear,srclin)))
            assert all(abs(x-y)<=1e-10*max(1,abs(y)) for x,y in zip(linear,srclin)), 'source normalization mismatch'
            refstream.seek(12*(xy[1]*4096+xy[0]))
            assert struct.unpack('<3f',refstream.read(12)) == tuple(ref), 'reference cache mismatch'
            group = ('black' if spread is None else 'nonblack-neutral' if spread<=.01 and ry>=.01
                     else 'nearblack-neutral' if spread<=.01 else 'chroma')
            lum = next((str(v) for v in (.01,.1,1,10,100,600) if ry<v),'above600')
            keys = ('all',group,'reference-Y<'+lum,group+'/reference-Y<'+lum)
            for k in keys:
                if math.isfinite(raw_is) and math.isfinite(im): rawshifts[k].append(720*(raw_is-im))
                if math.isfinite(is_) and math.isfinite(im): shifts[k].append(720*(is_-im))
            counters['Is_below_PQ0_projected_lattice']+=raw_is<pq_inverse(0)
            counters['Y_zero_achromatic_convention_lattice']+=Y==0
            try:
                if not all(math.isfinite(v) for v in values) or is_>1:
                    raise ValueError('invalid source/spatial scalar')
                mapped_y=pq_eotf(is_)
                restored=tuple(v*mapped_y/Y for v in linear) if Y>0 else (mapped_y,)*3
                observe('restored_RGB_nits',restored)
                counters['Y_zero_positive_Map_lattice']+=Y==0 and mapped_y>0
                if any(not math.isfinite(v) or not 0<=v<=10000 for v in restored):
                    raise ValueError('restored RGB outside physical PQ domain')
                q=pm.color_transform(tuple(pq_inverse(v) for v in restored),pm.BT2020_WEIGHTS,*d['CW_SG'])
                observe('postcolor_PQ',q)
                if any(not math.isfinite(v) or not 0<=v<=1 for v in q):
                    raise ValueError('post-color PQ outside physical domain')
                raw=tuple(pq_eotf(v) for v in q)
                nat=pm.apply_matrix(TO_P3,raw)
                observe('physical_P3_nits',nat)
                counters['physical_P3_negative_pixels']+=min(nat)<0
                counters['physical_P3_above600_pixels']+=max(nat)>600
                counters['physical_P3_excursion_pixels']+=min(nat)<0 or max(nat)>600
                clipped=tuple(min(600,max(0,v)) for v in nat)
                encoded_linear=tuple(max(0,v) for v in pm.apply_matrix(M,clipped))
                outq=tuple(pq_inverse(v) for v in encoded_linear)
                observe('encoded_PQ',outq)
                actual=rgb_to_itp(outq)
                e=delta_itp(actual,itp); res=tuple(720*(x-y) for x,y in zip(actual,itp))
                errors.append((e,res))
                for k in keys: bins[k].append((e,res))
                ra=rgb_to_itp(q); raw_errors.append((delta_itp(ra,itp),tuple(720*(x-y) for x,y in zip(ra,itp))))
                rows.append((xy,outq,e,res,720*(raw_is-im),720*(is_-im)))
            except (ValueError,OverflowError,ZeroDivisionError) as exc:
                invalid[str(exc)]+=1
                rows.append((xy,None,str(exc)))
    save(stage/'lattice-output.json',rows)
    complete = not invalid and not any(full[k] for k in ('source_invalid','scalar_invalid','spatial_invalid'))
    primary = metric_stats(errors) if complete else None
    passed = bool(primary and primary['mean']<=1 and primary['p95']<=3)
    worsened = bool(primary and (primary['mean']>BASELINES[shot][0] or primary['p95']>BASELINES[shot][1]))
    receipt = {'schema':'hdr.sol.gaussian357.result.v1','shot':shot,'scope':'sampled diagnostic NOT full-raster acceptance',
        'frozen_sha256':sha(OUT/'FROZEN.json'),'population':len(coords),'valid_lattice':len(errors),
        'coords_sha256':hashlib.sha256(b''.join(struct.pack('<II',*xy) for xy in coords)).hexdigest(),
        'source_cache_max_abs_disagreement':max_source_disagreement,'full_scalar_counters':full,
        'lattice_counters':dict(counters),'invalid_lattice':dict(invalid),'primary_all_population':primary,
        'output_ranges':{k:v if all(math.isfinite(x) for x in v) else None for k,v in ranges.items()},
        'partial_final_statistics':metric_stats(errors) if not complete else None,
        'raw_all_population':metric_stats(raw_errors) if complete else None,
        'strata':{k:metric_stats(v) for k,v in bins.items()},
        'signed720_Is_minus_Im_PROJECTED':{k:signed_stats(v) for k,v in shifts.items()},
        'signed720_Is_minus_Im_PREPROJECTION':{k:signed_stats(v) for k,v in rawshifts.items()},
        'lattice_fields_sha256':sha(stage/'lattice-fields.f64'),'lattice_output_sha256':sha(stage/'lattice-output.json'),
        'pass_1_3':passed,'worse_than_disclosed_current_lattice':worsened,
        'disposition':'REJECT_STOP_NO_VARIANTS' if not passed or worsened else 'FREEZE_REPORT_BEFORE_INTEGRATION',
        'units':0,'vendor_calls':0,'GPU_renders':0,'candidate_executions':1,'holdout_access':False,
        'seconds':time.time()-start}
    save(stage/'RESULT.json',receipt)
    print('RESULT',shot,json.dumps({k:receipt[k] for k in ('primary_all_population','invalid_lattice','full_scalar_counters','lattice_counters','disposition')}),flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif len(sys.argv)==3 and sys.argv[1]=='execute' and int(sys.argv[2]) in FILES:
        execute(int(sys.argv[2]))
    else:
        raise SystemExit('prepare | execute 256 | execute 714')
