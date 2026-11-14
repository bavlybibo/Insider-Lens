"""Stream exact accepted raw rows for a Canada query from its immutable disk index.

Output stays local, never auto-published. CSV includes original row/member/hash,
native fields, processing class, UTC and fixed grid. No inferred negative rows.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]

def run():
    p=argparse.ArgumentParser();p.add_argument('--month',required=True);p.add_argument('--source',choices=['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS'],required=True);p.add_argument('--pc',choices=['SP','NRT'],default='SP');p.add_argument('--daynight',choices=['ALL','D','N'],default='ALL');p.add_argument('--day');p.add_argument('--cell',help='fixed Canada cell ID, ca-...:10000:i:j');p.add_argument('--output',required=True);args=p.parse_args()
    query='SELECT member,row,source,pc,utc,i5>>1,j5>>1,hex(hash),raw FROM rows WHERE ym=? AND source=? AND pc=?';params=[args.month,args.source,args.pc]
    if args.daynight!='ALL':query+=' AND dn=?';params.append(args.daynight)
    if args.day:query+=' AND day=?';params.append(args.day)
    if args.cell:
        prefix,res,i,j=args.cell.rsplit(':',3);assert prefix=='ca-laea60n100w-wgs84-o0-v1' and res=='10000';query+=' AND (i5>>1)=? AND (j5>>1)=?';params.extend([int(i),int(j)])
    query+=' ORDER BY utc,member,row'
    db=sqlite3.connect(f'file:{(ROOT/"data/canada/native.sqlite").as_posix()}?mode=ro',uri=True);n=0
    # Exclusive creation prevents accidental overwrite of previously exported evidence.
    with Path(args.output).open('x',encoding='utf8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['member','raw_row','source','processing_class','utc','cell_i','cell_j','canonical_raw_sha256','native_record_json','observation_support','adjustment'])
        for row in db.execute(query,params):writer.writerow([*row,'OBSERVATION_UNKNOWN','ADJUSTMENT_WITHHELD']);n+=1
    print(json.dumps({'rows':n,'output':args.output,'selection':vars(args),'support':'UNKNOWN'}))

if __name__=='__main__':run()
