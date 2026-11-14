"""Independent raw-array recount and geometry arithmetic; no production reader imports."""
from collections import Counter
import datetime as dt
import hashlib
import json
import math
import os
import re
from pathlib import Path
import numpy as np
import h5py
from canada_oracle import project

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase8'
HANDLE=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run():
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());audit=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());mapped=json.loads((OUT/'MASK_CENTERS.json').read_text())
    manifest=json.loads((OUT/'DETAIL_DOWNLOAD_MANIFEST.json').read_text());rs={r['product']:r for r in manifest['receipts']};checks=[];display={};provenance=[]
    for name,geoname in [('MYD14','MYD03'),('VNP14','VNP03MOD'),('VNP14IMG','VNP03IMG')]:
        for product in [name,geoname]:assert digest(ROOT/rs[product]['file'])==rs[product]['sha256']
        modis=name=='MYD14';f=SD(str(ROOT/rs[name]['file']),SDC.READ) if modis else h5py.File(ROOT/rs[name]['file'],'r')
        g=SD(str(ROOT/rs[geoname]['file']),SDC.READ) if modis else h5py.File(ROOT/rs[geoname]['file'],'r')
        for handle,product in [(f,name),(g,geoname)]:
            if modis:
                core=handle.attributes()['CoreMetadata.0'];match=re.search(r'OBJECT\s*=\s*LOCALGRANULEID\s+.*?VALUE\s*=\s*"([^"\n]+)"',core,re.S);assert match;internal=match.group(1)
            else:
                internal=handle.attrs.get('LocalGranuleID',handle.attrs.get('product_name'))
                if isinstance(internal,np.ndarray):internal=internal.tolist()[0]
                if isinstance(internal,bytes):internal=internal.decode()
            assert internal==Path(rs[product]['file']).name
            provenance.append({'product':product,'internal_granule_id':internal,'payload_sha256':rs[product]['sha256'],'state':'PASS'})
        mask=f.select('fire mask') if modis else f['fire mask'];qa=f.select('algorithm QA') if modis else f['algorithm QA']
        lat=g.select('Latitude') if modis else g['geolocation_data/latitude'];lon=g.select('Longitude') if modis else g['geolocation_data/longitude'];zen=g.select('SensorZenith') if modis else g['geolocation_data/sensor_zenith']
        shape=mask.info()[2] if modis else mask.shape;points=[];bins={s:Counter() for s in [5000,10000,20000]};positive=Counter();controls=Counter();geo_bad=0;input_bad=0;bowtie=0
        w,s,e,n=c['aoi_wsen'];cw,cs,ce,cn=c['controls']['spatial_diagnostic_aoi']
        for row in range(0,shape[0],97):
            sl=np.s_[row:min(row+97,shape[0]),:];la=np.array(lat[sl]);lo=np.array(lon[sl]);mm=np.array(mask[sl]);qq=np.array(qa[sl]);zz=np.array(zen[sl])
            controls.update(map(int,mm[(la>=cs)&(la<cn)&(lo>=cw)&(lo<ce)]))
            rr,cc=np.where((la>=s)&(la<n)&(lo>=w)&(lo<e))
            for r,col in zip(rr,cc):
                m=int(mm[r,col]);q=int(qq[r,col]);z=int(zz[r,col])/100;longitude=float(lo[r,col]);latitude=float(la[r,col])
                points.append((row+int(r),int(col),longitude,latitude,m,q,z))
                x,y=project(longitude,latitude)
                for width in bins:bins[width][(math.floor(x/width),math.floor(y/width),m)]+=1
                if m in [7,8,9]:
                    positive['raw']+=1;positive['within40']+=int(z<=40)
                    if name=='VNP14IMG':
                        gf=int(g['geolocation_data/quality_flag'][row+r,col]);geo_bad+=int(gf!=0);input_bad+=int(q%128!=0);bowtie+=int((q//4194304)%2!=0)
                        positive['nominal375_within40']+=int(z<=40 and gf==0 and q%128==0 and (q//4194304)%2==0)
        got=sorted(points);expected=sorted(tuple(p[k] for k in ['line','sample','lon','lat','mask','qa','view_zenith_degrees']) for p in mapped[name]);assert got==expected
        hist=Counter(p[4] for p in got);assert {str(k):v for k,v in hist.items()}==audit['results'][name]['mask_counts']
        expected_cells=Counter({(p['i'],p['j'],int(mask)):number for p in audit['results'][name]['cells'] for mask,number in p['mask_counts'].items()})
        assert bins[10000]==expected_cells
        display[name]=[]
        for i,j in sorted({(i,j) for i,j,m in bins[5000]}):
            values={m:number for (x,y,m),number in bins[5000].items() if (x,y)==(i,j)}
            display[name].append({'i':i,'j':j,'count':sum(values.values()),'positive':sum(values.get(m,0) for m in [7,8,9]),'invalid':sum(values.get(m,0) for m in [0,1,2,4])})
        assert {str(k):v for k,v in controls.items()}==audit['spatial_diagnostic'][name]['mask_counts']
        assert len({(p[0],p[1]) for p in got})==len(got)
        # Sparse positive coordinates/FRP are independently read, not copied from audit.
        def read(key):
            ds=f.select(key) if modis else f[key]
            return np.array([]) if modis and np.prod(ds.info()[2])==0 else np.array(ds[:])
        slat=read('FP_latitude');slon=read('FP_longitude');power=read('FP_power');which=(slat>=s)&(slat<n)&(slon>=w)&(slon<e)
        assert int(which.sum())==positive['raw']
        frp=math.fsum(float(x) for x in power[which]);assert math.isclose(frp,audit['results'][name]['native_frp_mw_sum'],abs_tol=1e-10)
        if not modis:
            fp_rows=read('FP_line');fp_cols=read('FP_sample')
            for i in np.where(which)[0]:
                rr=int(fp_rows[i]);cc=int(fp_cols[i]);assert int(mask[rr,cc]) in [7,8,9]
                assert float(lat[rr,cc])==float(slat[i]) and float(lon[rr,cc])==float(slon[i])
        # Independently verify TAI93 scan bounds with raw scan arrays and rows.
        scans=sorted({p[0]//(10 if modis else 32 if name=='VNP14IMG' else 16) for p in got})
        starts=np.array(g.select('EV start time')[:]) if modis else np.array(g['scan_line_attributes/scan_start_time'])
        ends=starts[1:] if modis else np.array(g['scan_line_attributes/scan_end_time'])
        t=audit['results'][name]['scan_time_bounds'];assert min(starts[i] for i in scans)==t['tai93_min'];assert max(ends[i] for i in scans)==t['tai93_max']
        for key in ['min','max']:
            stamp=dt.datetime.fromisoformat(t['utc_start' if key=='min' else 'utc_end'].replace('Z','+00:00'))
            assert abs((stamp-dt.datetime(1993,1,1,tzinfo=dt.timezone.utc)).total_seconds()+10-t['tai93_'+key])<1e-5
        checks.append({'product':name,'identities':len(got),'mask_counts':dict(hist),'raw_positive_pixels':positive['raw'],'positive_screens':dict(positive),'positive_geolocation_bad':geo_bad,'positive_input_bad':input_bad,'positive_residual_bowtie':bowtie,'native_frp_mw_sum':frp,
                       'equal_area_bins':{str(k):len(v) for k,v in bins.items()},'spatial_control_mask_counts':dict(controls),'state':'PASS'})
        if modis:f.end();g.end()
        else:f.close();g.close()
    geometry=json.loads((OUT/'NOMINAL_GEOMETRY.json').read_text());maxerr=0
    # Fan triangulation is independent of production shoelace; checks stored nominal polygons.
    for p in geometry['polygons']:
        vertices=p['xy'];a=vertices[0];value=0
        for i in [1,2]:
            b=vertices[i];d=vertices[i+1];value+=abs((b[0]-a[0])*(d[1]-a[1])-(b[1]-a[1])*(d[0]-a[0]))/2
        sample=p['sample'];angle=.0014184397*(sample-676.5);R=6378.137;h=705;ratio=R/(R+h)
        d=math.sqrt(ratio*ratio-math.sin(angle)**2)
        expected_area=R*.0014184397*(math.cos(angle)/d-1)*(R+h)*.0014184397*(math.cos(angle)-d)*1e6
        err=abs(value/expected_area-1);maxerr=max(maxerr,err)
        assert err<1e-6,'Nominal local geometry arithmetic outside frozen tolerance'
    assert geometry['eligible_for_B1'] is False and audit['qualified_shared_support_m2'] is None
    result={'state':'PASS','support_audit_sha256':digest(OUT/'SUPPORT_AUDIT.json'),'mapped_centers_sha256':digest(OUT/'MASK_CENTERS.json'),
            'checks':checks,'nominal_geometry':{'polygons':len(geometry['polygons']),'max_relative_instrument_area_difference':maxerr,'arithmetic':'PASS','physical_boundaries':'NOT_QUALIFIED','clipped_union_and_overlap':'NOT_QUALIFIED'},
            'shared_domain':None,'calibration_validation':False,'human_signoff':False,'g4':'ADJUSTMENT_WITHHELD'}
    target=OUT/'INDEPENDENT_VALIDATION.json';raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    target=OUT/'INTERNAL_PROVENANCE.json';raw=(json.dumps({'state':'PASS','internal_ids':provenance,'manifest_sha256':digest(OUT/'DETAIL_DOWNLOAD_MANIFEST.json'),'exact_input_links':'all3 verified separately in SUPPORT_AUDIT.json; internal payload IDs now also match'},sort_keys=True,indent=2)+'\n').encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    target=OUT/'DISPLAY_BIN_RECOUNT.json';raw=(json.dumps({'mapped_centers_sha256':digest(OUT/'MASK_CENTERS.json'),'width_m':5000,'products':display},sort_keys=True,indent=2)+'\n').encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(json.dumps(result))

if __name__=='__main__':run()
