from datetime import datetime,timezone
from hypothesis import given,settings,strategies as st
from backend.tests.test_foundation import client
from backend.tests.test_recommendation_boundary import seed
from backend.selling_engine import optimize_selling
from backend.tests.test_optimizer_math import request

def body():
    costs={k:'0' for k in ('fixed_transport_inr','fixed_transaction_inr','transport_inr_per_quintal','handling_inr_per_quintal','market_fee_rate','commission_rate')};costs['assumptions']='TEST ONLY explicit zero charges'
    return {'crop':'c','market':'m','variety':'v','grade':'g','quantity':'10','buyer_price':'1000','required_cash':'5000','cash_deadline':datetime.now(timezone.utc).date().isoformat(),'storage':'no','storage_capacity':'0','safe_holding_days':0,'storage_evidence':'TEST ONLY no storage','minimum_lot':'1','quantity_increment':'1','market_step':'.01','today_costs':costs}
def test_immutable_access_and_recalculate(client):
    seed(client);response=client.post('/api/v1/recommend',json=body());assert response.status_code==200,response.text
    result=response.json();identifier=result['id'];headers={'X-Plan-Token':result['access_token']}
    assert result['selected_strategy']['cash_today_inr']=='10000.00'
    assert client.get('/api/v1/recommendations/'+identifier).status_code==404
    replay=optimize_selling(result['engine_input'])
    assert str(replay['recommended_plan']['cash_today_inr'])==result['selected_strategy']['cash_today_inr']
    original=client.get('/api/v1/recommendations/'+identifier,headers=headers).json()
    recalculated=client.post('/api/v1/recommendations/'+identifier+'/recalculate',json={**body(),'required_cash':'20000'},headers=headers)
    assert recalculated.status_code==200
    assert recalculated.json()['id']!=identifier
    assert recalculated.json()['feasibility_status']=='no_feasible_plan'
    assert client.get('/api/v1/recommendations/'+identifier,headers=headers).json()==original
    assert client.post('/api/v1/recommendations/compare',json=body()).status_code==200

def test_unknown_cost_and_forged_scenario(client):
    seed(client);b=body();del b['today_costs']['commission_rate'];assert client.post('/api/v1/recommend',json=b).status_code==422
    assert client.post('/api/v1/recommend',json={**body(),'scenarios':[]}).status_code==422

@given(quantity=st.integers(1,30),capacity=st.integers(0,30),cash=st.integers(0,40000))
@settings(max_examples=80,deadline=None)
def test_feasibility_properties(quantity,capacity,cash):
    r=request();r.update(total_quantity_quintals=str(quantity),storage_capacity_quintals=str(capacity),required_net_cash_inr=str(cash))
    result=optimize_selling(r)
    for p in result['feasible_plans']:
        assert p['sell_today_quintals']+p['hold_initial_quintals']==quantity
        assert p['hold_initial_quintals']<=capacity
        assert p['cash_today_inr']>=cash
        assert p['later_saleable_quintals']+p['deterioration_loss_quintals']+p['rounding_discard_quintals']==p['hold_initial_quintals']
