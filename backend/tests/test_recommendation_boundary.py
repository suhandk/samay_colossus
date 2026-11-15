from backend.tests.test_foundation import client
from backend.db import get_db
from backend.models import Crop,Market,DataSource
from backend.price_models import PriceImport,PriceRecord
from datetime import datetime,date,timezone

def seed(client):
    generator=get_db if False else client.app.dependency_overrides[get_db]
    with next(generator()) as db:
        db.add_all([Crop(id='c',names={'en':'TEST','kn':'TEST'},source_reference='fixture'),Market(id='m',names={'en':'TEST','kn':'TEST'},source_reference='fixture'),DataSource(id='s',reference='fixture')]);db.flush()
        b=PriceImport(source_id='s',retrieved_at=datetime.now(timezone.utc),imported_at=datetime.now(timezone.utc),file_hash='test',original_csv='TEST_ONLY',provenance={},counts={});db.add(b);db.flush()
        db.add(PriceRecord(identity_hash='test',record_hash='test',import_id=b.id,source_id='s',crop_id='c',market_id='m',variety='v',grade='g',observation_date=date(2020,1,1),minimum=900,modal=1000,maximum=1100,original_unit='INR/quintal',raw={},flags=[]));db.commit()

def body():return dict(crop='c',market='m',quantity='10',buyer='1000',cash='5000',storage='no',transport='100',labour='50',commission='0',other='0',kind='["v","g"]',increment='1',minimumLot='1',marketStep='.001')
def test_real_arithmetic_and_unknown_cost(client):
    seed(client);response=client.post('/api/v1/recommendations',json=body());assert response.status_code==200
    assert float(response.json()['optimization']['recommended_plan']['cash_today_inr'])==9850
    assert response.json()['scope']=='immediate_sale_only'
    assert client.post('/api/v1/recommendations',json={**body(),'transport':''}).status_code==422

def test_stale_reference_and_infeasible(client):
    seed(client)
    assert client.post('/api/v1/recommendations',json={**body(),'reference':True}).status_code==409
    result=client.post('/api/v1/recommendations',json={**body(),'cash':'20000'}).json()
    assert result['optimization']['recommended_plan'] is None

def test_malformed_request(client):assert client.post('/api/v1/recommendations',json={'quantity':'10'}).status_code==422

def test_holding_comparison_remains_conditional(client,monkeypatch):
    seed(client)
    from backend import decision_api as forecast_service
    monkeypatch.setattr(forecast_service,'forecast',lambda *args:{'price':1500,'intervals':[{'nominal_level':.9,'lower':1400,'upper':1600}],'flags':['research_only'],'model_version':'TEST ONLY'})
    request={**body(),'storage':'yes','capacity':'10','days':'3','storageCost':'10','loss':'0','futureTransport':'100','futureLabour':'50','futureCommission':'0','futureOther':'0','adversePrice':'1300','realization':'1','storageEvidence':'TEST ONLY safe storage','saleDateConfirmed':True,'increment':'1','minimumLot':'1','marketStep':'.001'}
    response=client.post('/api/v1/recommendations',json=request)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['scope']=='research_scenarios'
    held=[p for p in result['optimization']['comparison_plans'] if float(p['hold_initial_quintals'])>0]
    assert held and all(not p['recommendation_eligible'] for p in held)
    assert all(float(p['cash_today_inr'])>=5000 for p in held)
    assert float(result['optimization']['recommended_plan']['hold_initial_quintals'])==0
