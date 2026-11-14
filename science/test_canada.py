"""Adversarial intake and grid acceptance, plus actual published evidence when available."""
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from pyproj import Transformer
from canada_intake import objects,safe_members,parse,CRS,GRID
from canada_oracle import project,raw_objects
from canada_publish import grid_checks

ROOT=Path(__file__).resolve().parents[1]

class CanadaTests(unittest.TestCase):
    def row(self,**changes):
        return dict(latitude=52,longitude=-115,acq_date='2023-06-01',acq_time='0012',track=.5,version='2',frp=0,confidence='n',scan=.5,bright_t31=290,satellite='SNPP',brightness=310,instrument='SNPP',daynight='N',type='0',**changes)

    def test_streaming_json_chunk_boundaries_and_malformed_envelopes(self):
        rows=[self.row(),self.row()];raw=json.dumps(rows).encode()
        self.assertEqual(list(objects(io.BytesIO(raw),chunk=17)),rows)
        for invalid in [b'{}',b'[{"x":1}',b'[{"x":1},]',b'[] garbage',b'[1]']:
            with self.assertRaises(ValueError):list(objects(io.BytesIO(invalid),chunk=7))
        with self.assertRaises(ValueError):list(objects(io.BytesIO(b'[{"x":"'+b'x'*70000+b'"}]')))

    def test_independent_reader_and_raw_hash(self):
        rows=[self.row(),self.row()];raw=json.dumps(rows,indent=4).encode();h=hashlib.sha256()
        self.assertEqual(list(objects(io.BytesIO(raw),h,31)),list(raw_objects(io.BytesIO(raw))))
        self.assertEqual(h.hexdigest(),hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):list(raw_objects(io.BytesIO(raw[:-1])))

    def test_zip_guards_and_sp_nrt_multi_member(self):
        def archive(names):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                for n,content in names:z.writestr(n,content)
            out.seek(0);return zipfile.ZipFile(out)
        with archive([('fire_archive_M-C61_1.json','[]'),('fire_nrt_M-C61_1.json','[]'),('Readme.txt','NASA')]) as z:self.assertEqual(len(safe_members(z)),3)
        for name in ['../escape.json','C:/escape.json','/escape.json','executable.py','..\\bad.json']:
            with archive([(name,'[]')]) as z:
                with self.assertRaises(ValueError):safe_members(z)
        with archive([('fire_archive_test.json','0'*1000000)]) as z:
            with self.assertRaises(ValueError):safe_members(z)

    def test_corrupt_member_crc_is_not_accepted(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_STORED) as z:z.writestr('fire_archive_test.json','[]')
        raw=bytearray(out.getvalue());name='fire_archive_test.json';raw[30+len(name)]=ord('{')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            with self.assertRaises(zipfile.BadZipFile):list(objects(z.open(name)))

    def test_source_eras_utc_schema_and_literal_versions(self):
        row=self.row();source,utc,*_=parse(row,'845606');self.assertEqual(source,'SNPP_VIIRS');self.assertEqual(utc,'2023-06-01T00:12:00Z');self.assertEqual(row['version'],'2')
        for key,value in [('acq_time','2460'),('acq_date','2011-06-01'),('longitude',190),('daynight','?'),('confidence','100'),('instrument','MODIS'),('version',None)]:
            invalid={**row,key:value}
            if key=='version':invalid['unannounced_schema']='x'
            with self.assertRaises(ValueError):parse(invalid,'845606')
        self.assertEqual(parse({**row,'acq_date':'2012-01-20'},'845606')[0],source)
        with self.assertRaises(ValueError):parse({**row,'acq_date':'2012-01-19'},'845606')
        self.assertEqual(parse({**row,'acq_date':'2026-11-02','acq_time':'1540'},'845606')[0],source)
        with self.assertRaises(ValueError):parse({**row,'acq_date':'2026-11-02','acq_time':'1541'},'845606')
        self.assertEqual(parse({**row,'satellite':'Aqua','instrument':'MODIS','confidence':'100'},'845605')[0],'AQUA_MODIS')
        self.assertEqual(parse({**row,'satellite':'Terra','instrument':'MODIS','confidence':'0'},'845605')[0],'TERRA_MODIS')

    def test_canada_equal_area_high_latitude_axis_and_geodesic(self):
        result=grid_checks();self.assertEqual(result['state'],'PASS')
        transform=Transformer.from_crs('EPSG:4326',CRS,always_xy=True)
        for lon,lat in [(-123,49),(-80,70),(-53,47),(-140,80),(-100,60)]:
            xy=project(lon,lat);expected=transform.transform(lon,lat)
            self.assertLess(math.dist(xy,expected),.002)
        west=project(-101,60);east=project(-99,60);self.assertLess(west[0],0);self.assertGreater(east[0],0)
        self.assertEqual(math.floor(-.00001/10000),-1)

    def test_disk_duplicate_partition_and_negative_coarsening(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE r(member,hash UNIQUE)')
        db.executemany('INSERT OR IGNORE INTO r VALUES(?,?)',[('SP','a'),('SP','a'),('NRT','b')]);self.assertEqual(db.execute('SELECT COUNT(*) FROM r').fetchone()[0],2)
        for n in [-11,-4,-3,-1,0,1,3,4,11]:
            self.assertEqual(db.execute('SELECT ? >> 1',(n,)).fetchone()[0],math.floor(n/2))
            self.assertEqual(db.execute('SELECT ? >> 2',(n,)).fetchone()[0],math.floor(n/4))

    def test_frozen_preregistration_and_old_release(self):
        rule=json.loads((ROOT/'reports/CANADA_PREREGISTRATION.json').read_text(encoding='utf8'))
        self.assertEqual(rule['grid']['id'],GRID);self.assertEqual(rule['development']['months'],['2022-06','2023-06'])
        self.assertGreater(rule['geographic_holdout']['bbox'][1],rule['development']['bbox'][3])
        self.assertFalse(set(rule['development']['months'])&set(rule['temporal_holdout']['months']))
        self.assertEqual(hashlib.sha256((ROOT/'public/data/release.json').read_bytes()).hexdigest(),'e256a172f3c61b82f088428cc0b50554605fb0bdb4648f5410982be90a5f45ed')

if __name__=='__main__':unittest.main()
