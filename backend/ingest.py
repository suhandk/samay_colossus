"""Canonical CSV ingestion. Source-specific API integration is intentionally disabled."""
import argparse,csv,hashlib,io,json
from datetime import datetime,date,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from sqlalchemy import select
from .db import Session
from .models import Crop,Market,DataSource
from .price_models import PriceImport,PriceRecord,Quarantine

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def utcnow(): return datetime.now(timezone.utc)
def timestamp(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None: raise ValueError('Timestamp needs timezone')
    return result

def ingest(db,content,manifest):
    required=('source_id','source_url','license_url','retrieved_at','verified_by','column_mapping','crop_mapping','market_mapping')
    if any(not manifest.get(k) for k in required): raise ValueError('Incomplete provenance manifest')
    retrieved=timestamp(manifest['retrieved_at'])
    if retrieved>utcnow(): raise ValueError('Future retrieval timestamp')
    source=db.get(DataSource,manifest['source_id'])
    if not source: raise ValueError('Register reviewed source first')
    if source.reference!=manifest['source_url']: raise ValueError('Source reference mismatch')
    batch=PriceImport(source_id=source.id,retrieved_at=retrieved,imported_at=utcnow(),file_hash=digest(content),original_csv=content,provenance=manifest,counts={})
    db.add(batch);db.flush()
    counts={'accepted':0,'duplicates':0,'quarantined':0,'revisions':0,'flagged':0}
    reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    mapping=manifest['column_mapping']
    if not reader.fieldnames or any(v not in reader.fieldnames for v in mapping.values()): raise ValueError('CSV header does not match reviewed mapping')
    for number,raw in enumerate(reader,2):
        try:
            row={k:(raw.get(v) or '').strip() for k,v in mapping.items()}
            crop=manifest['crop_mapping'].get(row.get('crop'));market=manifest['market_mapping'].get(row.get('market'))
            if not crop or not market or not db.get(Crop,crop) or not db.get(Market,market): raise ValueError('Unmapped crop or market')
            if manifest.get('allowed_pairs') is not None and [crop,market] not in manifest['allowed_pairs']: raise ValueError('Unsupported crop-market mapping')
            observed=datetime.strptime(row['date'],manifest.get('date_format','%Y-%m-%d')).date()
            if observed>retrieved.date(): raise ValueError('Observation after retrieval')
            unit=row.get('unit') or manifest.get('unit')
            factor={'INR/quintal':Decimal(1),'INR/kg':Decimal(100),'INR/tonne':Decimal('0.1')}.get(unit)
            if factor is None: raise ValueError('Unknown units')
            prices=[Decimal(row[k])*factor for k in ('minimum','modal','maximum')]
            if any(not p.is_finite() or p<=0 or p>=Decimal('1000000000000') for p in prices): raise ValueError('Invalid price')
            if not prices[0]<=prices[1]<=prices[2]: raise ValueError('Inconsistent price range')
            variety=row.get('variety','');grade=row.get('grade','')
            if not variety or not grade: raise ValueError('Missing variety or grade')
            published=timestamp(row['published_at']) if row.get('published_at') else None
            identity=digest(json.dumps([source.id,crop,market,variety,grade,observed.isoformat()]))
            record=digest(json.dumps([str(p) for p in prices]+[unit,row.get('published_at','')]))
            previous=db.scalar(select(PriceRecord).where(PriceRecord.identity_hash==identity).order_by(PriceRecord.id.desc()))
            if previous and previous.record_hash==record: counts['duplicates']+=1;continue
            if previous and (not published or not previous.published_at or published.replace(tzinfo=None)<=previous.published_at.replace(tzinfo=None)):
                raise ValueError('Changed observation needs a newer source publication timestamp')
            flags=[]
            earlier=db.scalar(select(PriceRecord).where(PriceRecord.crop_id==crop,PriceRecord.market_id==market,PriceRecord.variety==variety,PriceRecord.grade==grade,PriceRecord.source_id==source.id,PriceRecord.observation_date<observed).order_by(PriceRecord.observation_date.desc(),PriceRecord.id.desc()))
            if earlier and abs(prices[1]/earlier.modal-1)>Decimal('0.5'): flags.append('price_change_over_50_percent')
            db.add(PriceRecord(identity_hash=identity,record_hash=record,import_id=batch.id,source_id=source.id,crop_id=crop,market_id=market,variety=variety,grade=grade,observation_date=observed,minimum=prices[0],modal=prices[1],maximum=prices[2],original_unit=unit,raw=raw,flags=flags,published_at=published,supersedes_id=previous.id if previous else None))
            db.flush();counts['accepted']+=1;counts['revisions']+=bool(previous);counts['flagged']+=bool(flags)
        except (ValueError,KeyError,InvalidOperation,TypeError) as error:
            db.add(Quarantine(import_id=batch.id,row_number=number,raw=raw,reason=str(error)));counts['quarantined']+=1
    batch.counts=counts;db.flush()
    return {'import_id':batch.id,**counts}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('manifest');args=parser.parse_args()
    with Session.begin() as db:
        print(json.dumps(ingest(db,Path(args.csv).read_text(encoding='utf-8-sig'),json.loads(Path(args.manifest).read_text(encoding='utf-8')))))
if __name__=='__main__':main()
