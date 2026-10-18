"""One frozen paragraph0078/Fig6 example hybrid; no old candidate execution."""
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

ROOT = Path('/work/hdr-nativehdr10-20261011')
OLD = ROOT/'t_77559dbf/gaussian357'
OUT = ROOT/'t_dc984464/edge366'
FRONT = ROOT/'t_bb5b2ce0/mastblack347/render-frontend355'
sys.dont_write_bytecode = True
sys.path.insert(0,str(FRONT))
from tools.dolby_harness import public_mapping as pm
from tools.dolby_harness.metric import delta_itp, pq_eotf, pq_inverse, rgb_to_itp, summarize

P3=((.68,.32),(.265,.69),(.15,.06),(.3127,.329))
BT=((.708,.292),(.17,.797),(.131,.046),(.3127,.329))
M=pm.convert_matrix(P3,BT)
TO_P3=pm.convert_matrix(BT,P3)
OLD_RESULTS={'256':'9f81a0dfcb19e8bd6f5e7ea6e4ed8a45d07ca0290101e7560b0b31c904c13888',
             '714':'a5fab901698181bdbca751a9db7a02e0d3bbf529d3717abbed6266b3c53b3572'}

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def save(p,obj):
    with p.open('x') as f: f.write(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def verify_front():
    sources=json.loads((FRONT/'SOURCES.json').read_text())
    for rel,digest in sources.items(): assert sha(FRONT/rel)==digest,rel
    return sources

def verify_old():
    assert sha(OLD/'FROZEN.json')=='dec75a80dd1d6fbacbbbd2fca1a70a5652f13d165cd4e89b424e8969248b03f8'
    frozen=json.loads((OLD/'FROZEN.json').read_text())
    for file,key in (('sol_gaussian357_diagnostic.py','script_sha256'),
                     ('sol_gaussian357_scalar.c','scalar_source_sha256'),
                     ('sol_gaussian357_contract.txt','contract_sha256'),
                     ('scalar','binary_sha256'),('COMPILE.json','compile_sha256')):
        assert sha(OLD/file)==frozen[key],file
    for shot,d in frozen['shots'].items():
        for key in ('manifest','source','reference_manifest','reference','cache','control'):
            assert sha(d[key])==d[key+'_sha256'],key
        result=OLD/shot/'RESULT.json'
        assert sha(result)==OLD_RESULTS[shot]
        r=json.loads(result.read_text())
        assert sha(OLD/shot/'lattice-fields.f64')==r['lattice_fields_sha256']
        assert (OLD/shot/'lattice-fields.f64').stat().st_size==34560*8*8
        assert not any(r['full_scalar_counters'][k] for k in ('source_invalid','scalar_invalid','spatial_invalid'))
    assert verify_front()==frozen['frontend_sources']
    return frozen

def prepare():
    old=verify_old()
    cmd=['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror',str(OUT/'sol_edge366_scalar.c'),'-lm','-o',str(OUT/'scalar')]
    p=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,TMPDIR=str(OUT)))
    save(OUT/'COMPILE.json',{'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,
        'compiler_version':subprocess.run(['cc','--version'],capture_output=True,text=True).stdout})
    assert p.returncode==0,p.stderr
    records={}
    for shot,d in old['shots'].items():
        r=json.loads((OLD/shot/'RESULT.json').read_text())
        records[shot]={'identities':d,'old_result_sha256':OLD_RESULTS[shot],
            'old_fields':str(OLD/shot/'lattice-fields.f64'),'old_fields_sha256':r['lattice_fields_sha256'],
            'inherited_old_metrics_NOT_recomputed':r['primary_all_population'],
            'old_coords_sha256':r['coords_sha256']}
    receipt={'schema':'hdr.sol.edge366.freeze.v1','shots':records,'old_frozen_sha256':sha(OLD/'FROZEN.json'),
        'frontend_sources':verify_front(),'frontend_sources_sha256':sha(FRONT/'SOURCES.json'),
        'script_sha256':sha(__file__),'scalar_source_sha256':sha(OUT/'sol_edge366_scalar.c'),
        'binary_sha256':sha(OUT/'scalar'),'compile_sha256':sha(OUT/'COMPILE.json'),
        'contract_sha256':sha(OUT/'sol_edge366_contract.txt'),
        'old_fields_schema':'little-endian binary64 RGB[3],Y,Io,Im,rawIs,projectedIs',
        'new_fields_schema':'little-endian binary64 dx,dy,alpha,rawIs,projectedIs',
        'XML_detail_minus_0_75':'UNRESOLVED_UNAPPLIED; not equated to public example weights',
        'MS_weight':0,'MS_edge_weight':1,'derivative_normalization_gain':'none; normalizedPQ already',
        'candidate_executions':0,'units':0,'holdout_access':False}
    save(OUT/'FROZEN.json',receipt)
    print('FROZEN',sha(OUT/'FROZEN.json'),flush=True)

def signed_stats(vals):
    if not vals:return None
    v=sorted(vals)
    return {'pixels':len(v),'mean':math.fsum(v)/len(v),'min':v[0],
        'p05':v[math.ceil(.05*len(v))-1],'p50':v[math.ceil(.5*len(v))-1],
        'p95':v[math.ceil(.95*len(v))-1],'max':v[-1],
        'mean_abs':math.fsum(abs(x) for x in v)/len(v),
        'negative':sum(x<0 for x in v),'zero':sum(x==0 for x in v),
        'one':sum(x==1 for x in v),'positive':sum(x>0 for x in v),'percentile':'nearest-rank'}

def metric_stats(rows):
    return {**summarize(v[0] for v in rows),
        'mean_signed720ITP':[math.fsum(v[1][i] for v in rows)/len(rows) for i in range(3)]} if rows else None

def execute(shot):
    frozen=json.loads((OUT/'FROZEN.json').read_text()); r=frozen['shots'][str(shot)]; d=r['identities']
    for file,key in ((__file__,'script_sha256'),(OUT/'scalar','binary_sha256'),
                     (OUT/'sol_edge366_scalar.c','scalar_source_sha256'),
                     (OUT/'sol_edge366_contract.txt','contract_sha256'),(OUT/'COMPILE.json','compile_sha256')):
        assert sha(file)==frozen[key],key
    verify_old()
    assert sys.byteorder=='little' and struct.calcsize('<8d')==64 and struct.calcsize('<5d')==40
    cache=json.loads(Path(d['cache']).read_text())
    prior=list(struct.iter_unpack('<8d',Path(r['old_fields']).read_bytes()))
    coords=[(x,y) for y in range(0,2160,16) for x in range(0,4096,16)]
    coordhash=hashlib.sha256(b''.join(struct.pack('<II',*xy) for xy in coords)).hexdigest()
    assert len(cache)==len(prior)==len(coords)==34560
    assert [tuple(v[0]) for v in cache]==coords and coordhash==r['old_coords_sha256']
    stage=OUT/str(shot); stage.mkdir(exist_ok=False)
    start=time.time()
    cmd=[str(OUT/'scalar'),d['control'],d['source'],r['old_fields'],str(stage/'edge-fields.f64')]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=700)
    save(stage/'EXECUTION.json',{'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.time()-start})
    assert p.returncode==0,p.stderr
    full=json.loads(p.stdout)
    fields=list(struct.iter_unpack('<5d',(stage/'edge-fields.f64').read_bytes()))
    assert len(fields)==34560
    counters=collections.Counter(); invalid=collections.Counter()
    bins=collections.defaultdict(list); shifts=collections.defaultdict(list); rawshifts=collections.defaultdict(list)
    alpha=[]; errors=[]; raw_errors=[]; rows=[]; max_source_disagreement=0.
    ranges={k:[math.inf,-math.inf] for k in ('restored_RGB_nits','postcolor_PQ','physical_P3_nits','encoded_PQ')}
    def observe(key,values):
        ranges[key][0]=min(ranges[key][0],min(values)); ranges[key][1]=max(ranges[key][1],max(values))
    with Path(d['reference']).open('rb') as refstream:
        for xy,entry,old,values in zip(coords,cache,prior,fields):
            _,srcpq,srclin,ref,itp,ry,spread,vol=entry
            linear,Y,io,im,oldraw,oldprojected=old[:3],*old[3:]
            dx,dy,a,raw_is,is_=values
            max_source_disagreement=max(max_source_disagreement,max(abs(x-y) for x,y in zip(linear,srclin)))
            assert all(abs(x-y)<=1e-10*max(1,abs(y)) for x,y in zip(linear,srclin))
            refstream.seek(12*(xy[1]*4096+xy[0])); assert struct.unpack('<3f',refstream.read(12))==tuple(ref)
            group=('black' if spread is None else 'nonblack-neutral' if spread<=.01 and ry>=.01 else 'nearblack-neutral' if spread<=.01 else 'chroma')
            lum=next((str(v) for v in (.01,.1,1,10,100,600) if ry<v),'above600')
            keys=('all',group,'reference-Y<'+lum,group+'/reference-Y<'+lum)
            for k in keys:
                if math.isfinite(raw_is):rawshifts[k].append(720*(raw_is-oldraw))
                if math.isfinite(is_):shifts[k].append(720*(is_-oldprojected))
            if math.isfinite(a):alpha.append(a)
            counters['Is_below_PQ0_projected_lattice']+=raw_is<pq_inverse(0)
            counters['Y_zero_achromatic_convention_lattice']+=Y==0
            try:
                if not all(math.isfinite(v) for v in (*old,*values)) or not 0<=a<=1 or is_>1:
                    raise ValueError('invalid neighborhood/spatial scalar')
                mapped_y=pq_eotf(is_)
                restored=tuple(v*mapped_y/Y for v in linear) if Y>0 else (mapped_y,)*3
                observe('restored_RGB_nits',restored)
                counters['Y_zero_positive_Map_lattice']+=Y==0 and mapped_y>0
                if any(not math.isfinite(v) or not 0<=v<=10000 for v in restored):raise ValueError('restored RGB outside physical PQ domain')
                q=pm.color_transform(tuple(pq_inverse(v) for v in restored),pm.BT2020_WEIGHTS,*d['CW_SG'])
                observe('postcolor_PQ',q)
                if any(not math.isfinite(v) or not 0<=v<=1 for v in q):raise ValueError('post-color PQ outside physical domain')
                raw=tuple(pq_eotf(v) for v in q); nat=pm.apply_matrix(TO_P3,raw)
                observe('physical_P3_nits',nat)
                counters['physical_P3_negative_pixels']+=min(nat)<0
                counters['physical_P3_above600_pixels']+=max(nat)>600
                counters['physical_P3_excursion_pixels']+=min(nat)<0 or max(nat)>600
                clipped=tuple(min(600,max(0,v)) for v in nat)
                outq=tuple(pq_inverse(max(0,v)) for v in pm.apply_matrix(M,clipped))
                counters['final_physical_P3_calls']+=1
                observe('encoded_PQ',outq)
                actual=rgb_to_itp(outq); e=delta_itp(actual,itp); res=tuple(720*(x-y) for x,y in zip(actual,itp))
                errors.append((e,res))
                for k in keys:bins[k].append((e,res))
                ra=rgb_to_itp(q); raw_errors.append((delta_itp(ra,itp),tuple(720*(x-y) for x,y in zip(ra,itp))))
                rows.append((xy,outq,e,res,values))
            except (ValueError,OverflowError,ZeroDivisionError) as exc:
                invalid[str(exc)]+=1
                rows.append((xy,None,str(exc)))
    # Preserve invalid fields by exact binary; JSON must never emit nonstandard NaN.
    save(stage/'lattice-output.json',[[*v[:4],list(v[4])] if len(v)==5 else v for v in rows])
    complete=not invalid and not any(full[k] for k in ('source_invalid','scalar_invalid','spatial_invalid','center_mismatch_components'))
    primary=metric_stats(errors) if complete else None
    passed=bool(primary and primary['mean']<=1 and primary['p95']<=3)
    result={'schema':'hdr.sol.edge366.result.v1','shot':shot,'scope':'sampled diagnostic NOT acceptance',
        'frozen_sha256':sha(OUT/'FROZEN.json'),'population':34560,'valid_lattice':len(errors),
        'coords_sha256':coordhash,'endian_schema_checked':True,'source_cache_max_abs_disagreement':max_source_disagreement,
        'full_neighborhood_counters':full,'lattice_counters':dict(counters),'invalid_lattice':dict(invalid),
        'primary_all_population':primary,'partial_final_statistics':metric_stats(errors) if not complete else None,
        'raw_all_population':metric_stats(raw_errors) if complete else None,
        'strata':{k:metric_stats(v) for k,v in bins.items()},'alpha':signed_stats(alpha),
        'strata_scope':'all-population' if complete else 'PARTIAL_ONLY_PRIMARY_UNAVAILABLE',
        'signed720_new_minus_old_PROJECTED':{k:signed_stats(v) for k,v in shifts.items()},
        'signed720_new_minus_old_PREPROJECTION':{k:signed_stats(v) for k,v in rawshifts.items()},
        'output_ranges':{k:v if all(math.isfinite(x) for x in v) else None for k,v in ranges.items()},
        'inherited_old_metrics_NOT_recomputed':r['inherited_old_metrics_NOT_recomputed'],
        'edge_fields_sha256':sha(stage/'edge-fields.f64'),'lattice_output_sha256':sha(stage/'lattice-output.json'),
        'pass_1_3':passed,'disposition':'FREEZE_AWAIT_ASTRA' if passed else 'REJECT_STOP_NO_VARIANTS',
        'candidate_executions':1,'old_candidate_executions':0,'old_metric_executions':0,'units':0,
        'GPU_renders':0,'vendor_calls':0,'holdout_access':False,'seconds':time.time()-start}
    save(stage/'RESULT.json',result)
    print('RESULT',shot,json.dumps({k:result[k] for k in ('primary_all_population','full_neighborhood_counters','lattice_counters','alpha','disposition')}),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=='execute' and sys.argv[2] in OLD_RESULTS:execute(int(sys.argv[2]))
    else:raise SystemExit('prepare | execute 256 | execute 714')
