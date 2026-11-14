"""Stream actual masks/QA/geolocation; reject inadequate common support.

No scalar scan/track rectangles or swath outlines stand in for pixel footprints.
No MODIS/750m QA bit meanings are borrowed from the distinct 375m product.
"""
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import time
import h5py
import numpy as np
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase6'
DLL_HANDLE=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC

def plain(v):
    if isinstance(v,(bytes,np.bytes_)):return v.decode(errors='replace')
    if isinstance(v,np.ndarray):return [plain(x) for x in v.tolist()] if v.ndim else plain(v.item())
    if isinstance(v,np.generic):return v.item()
    return v

def process(fire_path,geo_path,product,c,transform):
    hdf4=product=='MYD14'
    fire=SD(str(fire_path),SDC.READ) if hdf4 else h5py.File(fire_path,'r')
    geo=SD(str(geo_path),SDC.READ) if hdf4 else h5py.File(geo_path,'r')
    attrs={k:plain(v) for k,v in (fire.attributes() if hdf4 else fire.attrs).items()}
    mask=fire.select('fire mask') if hdf4 else fire['fire mask'];qa=fire.select('algorithm QA') if hdf4 else fire['algorithm QA']
    lat=geo.select('Latitude') if hdf4 else geo['geolocation_data/latitude'];lon=geo.select('Longitude') if hdf4 else geo['geolocation_data/longitude']
    zen=geo.select('SensorZenith') if hdf4 else geo['geolocation_data/sensor_zenith']
    raw_scale=float((zen.attributes() if hdf4 else zen.attrs)['scale_factor']) if hdf4 else float(zen.attrs['scale_factor'][0])
    assert abs(raw_scale-.01)<1e-8, 'Unexpected zenith scaling'
    # The declared 0.01-degree packed unit is stored as float32 by NetCDF.
    # Decode its decimal unit rather than imply precision from binary rounding.
    scale=.01
    shape=mask.info()[2] if hdf4 else list(mask.shape);gshape=lat.info()[2] if hdf4 else list(lat.shape);assert list(shape)==list(gshape)
    wanted=['ProcessVersionNumber','AlgorithmVersion','PGEVersion','ProductionTime','VersionID','StartTime','EndTime','DayNightFlag','InputFileGeo','InputPointer','MOD03 input file']
    metadata={k:attrs[k] for k in wanted if k in attrs}
    input_text=str(metadata.get('MOD03 input file',metadata.get('InputFileGeo',metadata.get('InputPointer',''))))
    expected=re.findall(r'(?:MYD03|VNP03IMG|VNP03MOD)\.A\d{7}\.\d{4}\.\d{3}\.\d+\.(?:hdf|nc)',input_text)
    lineage=geo_path.name in expected
    hist=Counter();qhist=Counter();views={str(v):Counter() for v in [30,40,50]};cells=defaultdict(lambda:Counter());examples=[];zmin=180.;zmax=-1.;count=0;geobad=0;nominal_375=0;residual_bowtie=0
    w,s,e,n=c['aoi_wsen']
    for start in range(0,shape[0],64):
        stop=min(start+64,shape[0]);sl=np.s_[start:stop,:]
        la=np.asarray(lat[sl]);lo=np.asarray(lon[sl]);zz=np.asarray(zen[sl],dtype=np.float64)*scale
        inside=(la>=s)&(la<n)&(lo>=w)&(lo<e)&np.isfinite(la)&np.isfinite(lo)
        if not np.any(inside):continue
        mm=np.asarray(mask[sl]);qq=np.asarray(qa[sl],dtype=np.uint32);count+=int(inside.sum())
        values,numbers=np.unique(mm[inside],return_counts=True);hist.update({int(a):int(b) for a,b in zip(values,numbers)})
        values,numbers=np.unique(qq[inside],return_counts=True);qhist.update({int(a):int(b) for a,b in zip(values,numbers)})
        validz=inside&(zz>=0)&(zz<=180);zmin=min(zmin,float(zz[validz].min()));zmax=max(zmax,float(zz[validz].max()))
        nominal=inside.copy()
        if not hdf4:
            gf=np.asarray(geo['geolocation_data/quality_flag'][sl]);geobad+=int((inside&(gf!=0)).sum());nominal&=(gf==0)
        if product=='VNP14IMG':
            nominal&=((qq&127)==0)&((qq&(1<<22))==0);nominal_375+=int(nominal.sum());residual_bowtie+=int((inside&((qq&(1<<22))!=0)).sum())
        for v in [30,40,50]:
            view=validz&(zz<=v);screen=view&np.isin(mm,[5,7,8,9]);views[str(v)].update({'aoi_centers_within_view':int(view.sum()),'mask_land_or_fire_centers_within_view':int(screen.sum()),
                'fully_QA_screened_375m_centers':int((screen&nominal).sum()) if product=='VNP14IMG' else 0})
        xs,ys=transform.transform(lo[inside],la[inside]);ii=np.floor(np.asarray(xs)/10000).astype(int);jj=np.floor(np.asarray(ys)/10000).astype(int)
        flatmask=mm[inside];flatz=zz[inside]
        for i,j,m,z in zip(ii,jj,flatmask,flatz):cells[(int(i),int(j))][int(m)]+=1
        if len(examples)<12:
            rr,cc=np.where(inside)
            for row,col in zip(rr[:12-len(examples)],cc[:12-len(examples)]):examples.append({'line':start+int(row),'sample':int(col),'lon':float(lo[row,col]),'lat':float(la[row,col]),'mask':int(mm[row,col]),'qa':int(qq[row,col]),'view_zenith_degrees':float(zz[row,col])})
    table={k:str(v) for k,v in (mask.attributes() if hdf4 else mask.attrs).items() if k=='legend'}
    sparse={}
    for name in ['FP_latitude','FP_longitude','FP_power','FP_ViewZenAng','FP_confidence']:
        if hdf4:
            ds=fire.select(name);arr=np.array([],dtype=float) if np.prod(ds.info()[2])==0 else np.asarray(ds[:])
        else:arr=np.asarray(fire[name][:])
        sparse[name]=arr
    la=sparse['FP_latitude'];lo=sparse['FP_longitude'];which=(la>=s)&(la<n)&(lo>=w)&(lo<e)
    fp=[{name:plain(arr[i]) for name,arr in sparse.items()} for i in np.where(which)[0]]
    if hdf4:fire.end();geo.end()
    else:fire.close();geo.close()
    return {'product':product,'shape':list(shape),'aoi_pixel_centers':count,'mask_counts':dict(sorted(hist.items())),
        'qa_word_counts':dict(sorted(qhist.items())),'view_zenith_min_degrees':zmin if count else None,'view_zenith_max_degrees':zmax if count else None,
        'view_sensitivity':{k:{**dict(v),'fully_QA_screened_375m_centers':v['fully_QA_screened_375m_centers'] if product=='VNP14IMG' else None} for k,v in views.items()},'nonzero_geolocation_quality_centers':geobad if not hdf4 else None,
        'qa_375m_nominal_no_residual_bowtie_centers':nominal_375 if product=='VNP14IMG' else None,
        'qa_375m_residual_bowtie_centers':residual_bowtie if product=='VNP14IMG' else None,
        'qa_interpretation':'C2 375m bits0:6 nominal and bit22 no residual bowtie + geolocation flags zero' if product=='VNP14IMG' else 'raw words retained; exact MODIS/750m algorithm bit policy NOT QUALIFIED. View rejection alone is sufficient to reject primary sample.',
        'geolocation_input_named':expected,'downloaded_geolocation':geo_path.name,'exact_geolocation_input_identity':lineage,
        'fire_metadata':metadata,'view_scale_factor_raw':raw_scale,'view_decoded_unit_degrees':scale,'mask_legend':table,'aoi_sparse_fire_pixels':fp,'examples':examples,
        'cells':[{'i':i,'j':j,'mask_counts':dict(sorted(h.items()))} for (i,j),h in sorted(cells.items())],
        'meaning':'measured native mask classes at geolocated centers; NOT cloud-free area, complete cell exposure, exact footprints or wildfire absence'}

def run():
    started=time.perf_counter();c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());manifest=json.loads((OUT/'L2_DOWNLOAD_MANIFEST.json').read_text())
    receipts={(r['day'],r['product']):r for r in manifest['receipts']}
    for r in receipts.values():
        with (ROOT/r['file']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
    transform=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True);results={}
    for day in c['l2_discovery_days']:
        results[day]={}
        for fire,geo in [('MYD14','MYD03'),('VNP14','VNP03MOD'),('VNP14IMG','VNP03IMG')]:
            if (day,fire) not in receipts:continue
            results[day][fire]=process(ROOT/receipts[day,fire]['file'],ROOT/receipts[day,geo]['file'],fire,c,transform)
    selection=json.loads((OUT/'L2_SELECTION.json').read_text())
    audit={'state':'FROZEN_COMMON_SUPPORT_REJECTED','classification':'B1_GEOMETRY_ONLY','science_files':manifest['science_files'],'downloaded_bytes':manifest['total_bytes'],
        'results':results,'nominal_offsets_minutes':{s['day']:s['nominal_start_offset_minutes'] for s in selection['selection']},
        'primary_eligible_shared_support':0,'qualified_observation_denominator':None,
        'rejections':['Primary June1: all Aqua and VIIRS AOI centers exceed even50deg sensitivity limit; no eligible common support under frozen30/40/50deg rules.',
            'Replication June8: nominal41min exceeds primary30min; Aqua has no AOI center <=40deg.',
            'Aqua downloaded MYD03 is a different processing instance from exact MYD03 input named in MYD14; unresolved source-instance pairing.',
            'Exact MODIS/750m QA-bit qualification and shared pixel footprints not established. Raw center masks are not an exposure denominator.'],
        'hypothesis_result':'750m files actually decoded alongside375m; primary sample cannot test continuity/calibration because no eligible common support. No FRP fit or count factor.',
        'g4':c['gate'],'elapsed_seconds':time.perf_counter()-started}
    (OUT/'L2_SUPPORT_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    common=json.loads((OUT/'COMMON_SUPPORT_AUDIT.json').read_text());common['support'].update({'downloaded_decoded_masks':5,'science_files':manifest['science_files'],'downloaded_bytes':manifest['total_bytes'],'primary_eligible_shared_support':0,'actual_l2_evidence':'reports/phase6/L2_SUPPORT_AUDIT.json'})
    common['B2']={'state':'REJECTED_FROZEN_SUPPORT','reason':audit['hypothesis_result']};common['B3']={'state':'NOT_IDENTIFIABLE_ON_FROZEN_SAMPLE','reason':'Valid raw MW FRP present; no qualified shared support, oriented footprints or applicable calibration samples. No coefficients fitted.'}
    (OUT/'COMMON_SUPPORT_AUDIT.json').write_text(json.dumps(common,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'state':audit['state'],'seconds':audit['elapsed_seconds'],'counts':{d:{p:{k:v[k] for k in ['aoi_pixel_centers','mask_counts','view_zenith_min_degrees','view_zenith_max_degrees','exact_geolocation_input_identity']} for p,v in ps.items()} for d,ps in results.items()}}))

if __name__=='__main__':run()
