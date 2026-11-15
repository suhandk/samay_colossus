"""Import hash-verified official archives from the user-supplied bundle only."""
import argparse,sqlite3,json,hashlib
from pathlib import Path
from datetime import datetime,date,timezone
from decimal import Decimal
from sqlalchemy import select
from .db import Session
from .models import Crop,Market,DataSource
from .price_models import PriceImport,PriceRecord
from .ingest import digest

def run(root):
    config=json.loads(Path('config/supplied-catalog.json').read_text(encoding='utf-8'))
    source=sqlite3.connect(f'file:{(root/"data/prepared/samay.db").as_posix()}?mode=ro',uri=True);source.row_factory=sqlite3.Row
    crops={e['source_name']:e for e in config['crops']};markets={e['source_name']:e for e in config['markets']}
    counts={'inserted':0,'duplicate':0,'excluded':0,'batches':0}
    with Session.begin() as db:
        for cls,entries,table in ((Crop,config['crops'],'commodities'),(Market,config['markets'],'markets')):
            for e in entries:
                if not source.execute(f'SELECT 1 FROM {table} WHERE name=?',(e['source_name'],)).fetchone():raise ValueError('Unverified catalog name')
                db.merge(cls(id=e['id'],names=e['names'],source_reference='User-supplied AGMARKNET archive; retained import provenance'))
        db.flush()
        batches={}
        for row in source.execute("SELECT o.*, c.name crop_name,m.name market_name FROM mandi_observations o JOIN commodities c ON c.id=o.commodity_id JOIN markets m ON m.id=o.market_id"):
            r=dict(row)
            if r['data_kind']!='official' or r['crop_name'] not in crops or r['market_name'] not in markets:counts['excluded']+=1;continue
            b=dict(source.execute('SELECT * FROM import_batches WHERE id=?',(r['latest_batch_id'],)).fetchone())
            if b['data_kind']!='official':raise ValueError('Provenance mismatch')
            path=(root/b['archive_path']).resolve()
            if not path.is_relative_to(root.resolve()):raise ValueError('Archive escapes bundle')
            if b['id'] not in batches:
                raw=path.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=b['file_sha256']:raise ValueError('Archive hash mismatch')
                sid='bundle-'+str(b['id']);db.merge(DataSource(id=sid,reference=b['source_url']));db.flush()
                batch=db.scalar(select(PriceImport).where(PriceImport.source_id==sid,PriceImport.file_hash==b['file_sha256']))
                if not batch:
                    batch=PriceImport(source_id=sid,retrieved_at=datetime.fromisoformat(b['fetched_at']).replace(tzinfo=timezone.utc),imported_at=datetime.now(timezone.utc),file_hash=b['file_sha256'],original_csv=raw.decode('utf-8-sig'),provenance={'original_manifest':json.loads(b['manifest']),'source_label':b['source_label'],'source_url':b['source_url'],'data_kind':'official','bundle_batch_id':b['id']},counts={})
                    db.add(batch);db.flush();counts['batches']+=1
                batches[b['id']]=batch
            batch=batches[b['id']];cid=crops[r['crop_name']]['id'];mid=markets[r['market_name']]['id']
            identity=digest(json.dumps([batch.source_id,cid,mid,r['variety'],r['grade'],r['observed_on']]))
            if db.scalar(select(PriceRecord.id).where(PriceRecord.identity_hash==identity)):counts['duplicate']+=1;continue
            values=[Decimal(str(r[k])) for k in ('min_price_inr_per_quintal','modal_price_inr_per_quintal','max_price_inr_per_quintal')]
            if not 0<values[0]<=values[1]<=values[2] or r['price_unit']!='INR/quintal':raise ValueError('Invalid supplied price')
            db.add(PriceRecord(identity_hash=identity,record_hash=digest(json.dumps(r,sort_keys=True)),import_id=batch.id,source_id=batch.source_id,crop_id=cid,market_id=mid,variety=r['variety'],grade=r['grade'],observation_date=date.fromisoformat(r['observed_on']),minimum=values[0],modal=values[1],maximum=values[2],original_unit=r['price_unit'],raw=r,flags=[],published_at=None))
            counts['inserted']+=1
        for batch in batches.values():batch.counts={'imported_from_verified_bundle':True}
    return counts
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);args=parser.parse_args();print(json.dumps(run(args.root)))
