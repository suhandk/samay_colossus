from datetime import date
import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from backend.db import Base
from backend.models import Crop,Market,DataSource
from backend.price_models import PriceRecord,Quarantine,PriceImport
from backend.ingest import ingest
from backend.prices_api import freshness
from backend.tests.test_foundation import client
@pytest.fixture
def db():
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Crop(id='c',names={'en':'TEST','kn':'TEST'},source_reference='fixture'),Market(id='m',names={'en':'TEST','kn':'TEST'},source_reference='fixture'),DataSource(id='test',reference='https://example.invalid')]);db.commit();yield db

def manifest():return {'source_id':'test','source_url':'https://example.invalid','license_url':'fixture','retrieved_at':'2026-01-03T00:00:00Z','verified_by':'test','column_mapping':{k:k for k in ['crop','market','date','minimum','modal','maximum','unit','variety','grade','published_at']},'crop_mapping':{'TEST':'c'},'market_mapping':{'TEST':'m'}}
def csv(modal='20',date='2026-01-01',unit='INR/kg',published='2026-01-02T00:00:00Z'):
    return 'crop,market,date,minimum,modal,maximum,unit,variety,grade,published_at\nTEST,TEST,'+date+',10,'+modal+',30,'+unit+',v,g,'+published+'\n'
def test_duplicate_and_conversion(db):
    assert ingest(db,csv(),manifest())['accepted']==1
    assert ingest(db,csv(),manifest())['duplicates']==1
    assert db.scalar(select(PriceRecord)).modal==2000
    assert db.scalar(select(func.count()).select_from(PriceRecord))==1
@pytest.mark.parametrize('content',[csv('-1'),csv(date=''),csv(unit='unknown'),csv('40'),csv().replace(',v,g,',',,g,')])
def test_quarantine(db,content):
    assert ingest(db,content,manifest())['quarantined']==1
    assert db.scalar(select(func.count()).select_from(PriceRecord))==0
    assert db.scalar(select(Quarantine)).raw

def test_revision(db):
    ingest(db,csv(),manifest());result=ingest(db,csv('21',published='2026-01-03T00:00:00Z'),manifest())
    assert result['revisions']==1
    assert db.scalar(select(func.count()).select_from(PriceRecord))==2
    assert ingest(db,csv(),manifest())['quarantined']==1

def test_unmapped(db):
    assert ingest(db,csv().replace('TEST,TEST','UNKNOWN,TEST'),manifest())['quarantined']==1

def test_freshness():
    assert freshness(date(2026,1,1),date(2026,1,2))=='current'
    assert freshness(date(2026,1,1),date(2026,1,4))=='delayed'
    assert freshness(date(2026,1,1),date(2026,1,5))=='stale'

def test_apis(client):
    for route in ['crops','markets','markets/availability','prices/history','prices/coverage','data/status','data/sources']:
        response=client.get('/api/v1/'+route);assert response.status_code==200;assert 'generated_at' in response.json()
    assert client.get('/api/v1/prices/latest?crop=c&market=m&variety=v&grade=g').json()['status']=='unavailable'
    assert client.get('/api/v1/prices/history?start=2026-02-01&end=2026-01-01').status_code==422

def test_raw_restoration(db):
    ingest(db,csv(),manifest());batch=db.scalar(select(PriceImport));raw=batch.original_csv;provenance=batch.provenance
    db.query(PriceRecord).delete();db.flush()
    assert ingest(db,raw,provenance)['accepted']==1
    assert db.scalar(select(PriceRecord)).modal==2000
