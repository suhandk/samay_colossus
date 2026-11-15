from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy import select,func
from .db import get_db
from .models import Crop,Market,DataSource
from .price_models import PriceRecord,PriceImport,Quarantine
router=APIRouter(prefix='/api/v1')
def now(): return datetime.now(timezone.utc)
def freshness(observed,today=None):
    days=((today or now().astimezone(ZoneInfo("Asia/Kolkata")).date())-observed).days
    return 'unavailable' if days<0 else 'current' if days<=1 else 'delayed' if days<=3 else 'stale'
def envelope(items):return {'generated_at':now(),'items':items}
@router.get('/crops')
def crops(db=Depends(get_db)):return envelope([{'id':c.id,'names':c.names,'source':c.source_reference} for c in db.scalars(select(Crop))])
@router.get('/markets')
def markets(db=Depends(get_db)):return envelope([{'id':c.id,'names':c.names,'source':c.source_reference} for c in db.scalars(select(Market))])
def query_records(db,crop,market,variety,grade,start,end):
    if start and end and start>end:raise HTTPException(422,'Start date is after end date')
    latest=select(PriceRecord.identity_hash,func.max(PriceRecord.id).label('id')).group_by(PriceRecord.identity_hash).subquery()
    stmt=select(PriceRecord).join(latest,PriceRecord.id==latest.c.id)
    for column,value in ((PriceRecord.crop_id,crop),(PriceRecord.market_id,market),(PriceRecord.variety,variety),(PriceRecord.grade,grade)):
        if value is not None:stmt=stmt.where(column==value)
    if start:stmt=stmt.where(PriceRecord.observation_date>=start)
    if end:stmt=stmt.where(PriceRecord.observation_date<=end)
    return stmt.order_by(PriceRecord.observation_date.desc(),PriceRecord.id.desc())
def serialize(db,p):
    batch=db.get(PriceImport,p.import_id);source=db.get(DataSource,p.source_id)
    retrieval=db.scalar(select(func.max(PriceImport.retrieved_at)).where(PriceImport.file_hash==batch.file_hash,PriceImport.source_id==p.source_id))
    return {'id':p.id,'crop_id':p.crop_id,'market_id':p.market_id,'market':db.get(Market,p.market_id).names,'variety':p.variety,'grade':p.grade,'observation_date':p.observation_date,'minimum':str(p.minimum),'modal':str(p.modal),'maximum':str(p.maximum),'unit':'INR/quintal','original_unit':p.original_unit,'source':{'id':source.id,'url':source.reference},'retrieved_at':retrieval,'published_at':p.published_at,'freshness':freshness(p.observation_date),'flags':p.flags,'import_id':p.import_id,'record_hash':p.record_hash}
@router.get('/prices/history')
def history(crop:str|None=None,market:str|None=None,variety:str|None=None,grade:str|None=None,start:date|None=None,end:date|None=None,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=1000),db=Depends(get_db)):
    stmt=query_records(db,crop,market,variety,grade,start,end)
    rows=db.scalars(stmt.offset(offset).limit(limit)).all()
    return {**envelope([serialize(db,p) for p in rows]),'offset':offset,'limit':limit,'status':'available' if rows else 'unavailable'}
@router.get('/prices/latest')
def latest(crop:str,market:str,variety:str,grade:str,db=Depends(get_db)):
    p=db.scalar(query_records(db,crop,market,variety,grade,None,None).limit(1))
    return {**envelope([serialize(db,p)] if p else []),'status':freshness(p.observation_date) if p else 'unavailable'}
@router.get('/prices/coverage')
@router.get('/markets/availability')
def coverage(crop:str|None=None,market:str|None=None,variety:str|None=None,grade:str|None=None,start:date|None=None,end:date|None=None,db=Depends(get_db)):
    rows=db.scalars(query_records(db,crop,market,variety,grade,start,end)).all();items=[]
    for c in db.scalars(select(Crop)):
        if crop and crop!=c.id:continue
        for m in db.scalars(select(Market)):
            if market and market!=m.id:continue
            selected=[r for r in rows if r.crop_id==c.id and r.market_id==m.id]
            items.append({'crop_id':c.id,'market_id':m.id,'count':len(selected),'status':'available' if selected else 'unavailable','start':min((r.observation_date for r in selected),default=None),'end':max((r.observation_date for r in selected),default=None),'sources':sorted({r.source_id for r in selected}),'varieties_grades':sorted({(r.variety,r.grade) for r in selected})})
    return envelope(items)
@router.get('/data/sources')
def sources(db=Depends(get_db)):return envelope([{'id':s.id,'url':s.reference} for s in db.scalars(select(DataSource))])
@router.get('/data/status')
def status(db=Depends(get_db)):
    batches=db.scalars(select(PriceImport).order_by(PriceImport.id.desc()).limit(50)).all()
    return {**envelope([{'id':b.id,'source_id':b.source_id,'retrieved_at':b.retrieved_at,'imported_at':b.imported_at,'counts':b.counts} for b in batches]),'records':db.scalar(select(func.count()).select_from(PriceRecord)),'quarantined':db.scalar(select(func.count()).select_from(Quarantine)),'api_adapter':'unavailable: response contract not verified'}
