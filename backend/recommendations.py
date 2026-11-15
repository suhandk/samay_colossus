from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel,ConfigDict
from sqlalchemy import select
from .db import get_db
from .models import Crop,Market,SellingPlan,Calculation
from .price_models import PriceRecord
from .prices_api import freshness,serialize
from .selling_engine import optimize_selling
router=APIRouter()
class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    crop:str;market:str;quantity:str;buyer:str;cash:str;due:str='';storage:str;capacity:str='';days:str='';storageCost:str='';loss:str='';transport:str='';labour:str='';commission:str='';other:str='';reference:bool=False;kind:str='';futureTransport:str='';futureLabour:str='';futureCommission:str='';futureOther:str='';adversePrice:str='';realization:str='';storagePayment:str='later';increment:str='';minimumLot:str='';marketStep:str='';risk:str='conservative';storageEvidence:str='';saleDateConfirmed:bool=False

class PlanLedger(BaseModel):
    model_config=ConfigDict(extra='allow')
    transport_inr:str;handling_inr:str;commission_inr:str;fixed_transaction_inr:str;market_fee_inr:str
class PlanOutput(BaseModel):
    model_config=ConfigDict(extra='allow')
    sell_today_quintals:str;hold_initial_quintals:str;cash_today_inr:str
    total_net_inr:dict[str,str]
    storage_cost_inr:str;holding_days:int;proposed_sale_date:str
    central_later_net_after_storage_inr:str;deterioration_loss_quintals:str
    break_even_future_price_inr_per_quintal:str|None
    recommendation_eligible:bool;today_sale:PlanLedger
    difference_vs_sell_all_now_inr:dict[str,str]
class OptimizationOutput(BaseModel):
    model_config=ConfigDict(extra='allow')
    status:str;recommended_plan:PlanOutput|None;feasible_plans:list[PlanOutput];comparison_plans:list[PlanOutput]
class PlannerResponse(BaseModel):
    model_config=ConfigDict(extra='allow')
    id:str;generated_at:str;inputs:Draft;optimization:OptimizationOutput
    scope:str;reference_price_based:bool;access_token:str


def amount(value,name,positive=False):
    try:result=Decimal(value)
    except InvalidOperation:raise HTTPException(422,{'code':'unknown_cost_or_value','field':name})
    if not result.is_finite() or result<0 or result>Decimal('1000000000') or (positive and result==0):raise HTTPException(422,{'code':'invalid_value','field':name})
    return result

def from_draft(body,db,parent=None,token=None):
    import json
    from datetime import date,timedelta
    from zoneinfo import ZoneInfo
    from .decision_api import DecisionInput,compute,persist,read
    prior=read(db,parent,token) if parent else None
    try:variety,grade=json.loads(body.kind)
    except (ValueError,TypeError):raise HTTPException(422,{'code':'select_variety_grade'})
    def costs(prefix=''):
        names=('transport','labour','commission','other') if not prefix else ('futureTransport','futureLabour','futureCommission','futureOther')
        transport,labour,commission,other=[amount(getattr(body,k),k) for k in names]
        return {'fixed_transport_inr':transport,'fixed_transaction_inr':labour+commission+other,'transport_inr_per_quintal':0,'handling_inr_per_quintal':0,'market_fee_rate':0,'commission_rate':0,'assumptions':'Farmer entered total charges per transaction; labour, commission and other are fixed quoted totals. Variable costs included in those totals.'}
    options=[];missing=[]
    if body.storage=='yes':
        required=('days','capacity','storageCost','loss','futureTransport','futureLabour','futureCommission','futureOther','adversePrice','realization','storageEvidence')
        missing=[k for k in required if not str(getattr(body,k)).strip()]
        if not missing:
            try:days=int(body.days)
            except ValueError:raise HTTPException(422,{'code':'invalid_days'})
            if days not in (1,3,7):raise HTTPException(422,{'code':'unsupported_horizon'})
            loss=amount(body.loss,'loss')/100
            options=[{'days':days,'daily_loss_fractions':[0]*(days-1)+[loss],'daily_storage_inr_per_quintal':[0]*days,'fixed_storage_inr':amount(body.storageCost,'storageCost'),'storage_payment':body.storagePayment,'future_sale_costs':costs('future'),'assumptions':'Farmer total storage charge applies to any held quantity; total loss applied at final sale','sale_date_availability':'confirmed' if body.saleDateConfirmed else 'unknown','realization_multiplier':amount(body.realization,'realization',True),'adverse_price':amount(body.adversePrice,'adversePrice')}]
    try:
        request=DecisionInput(crop=body.crop,market=body.market,variety=variety,grade=grade,quantity=amount(body.quantity,'quantity',True),buyer_price=None if body.reference else amount(body.buyer,'buyer',True),reference_scenario=body.reference,required_cash=amount(body.cash,'cash'),cash_deadline=date.fromisoformat(body.due) if body.due else datetime.now(ZoneInfo('Asia/Kolkata')).date(),storage=body.storage,storage_capacity=amount(body.capacity,'capacity') if body.storage=='yes' else 0,safe_holding_days=int(body.days) if body.storage=='yes' and body.days else 0,storage_evidence=body.storageEvidence or 'No verified storage evidence supplied; holding not evaluated',minimum_lot=amount(body.minimumLot,'minimumLot',True),quantity_increment=amount(body.increment,'increment',True),market_step=amount(body.marketStep,'marketStep',True),today_costs=costs(),risk=body.risk,holding_options=tuple(options))
        result=compute(request,db)
    except ValueError as error:raise HTTPException(422,{'code':'invalid_input','reason':str(error)})
    if missing:result['unresolved_assumptions'].append({'code':'missing_holding_assumptions','fields':missing})
    optimization=result['optimization'];groups={}
    for plan in optimization['feasible_plans']:
        plan['proposed_sale_date']=(datetime.fromisoformat(result['generated_at']).astimezone(ZoneInfo('Asia/Kolkata')).date()+timedelta(days=plan['holding_days'])).isoformat()
        kind='now' if not plan['holding_days'] else 'hold' if not Decimal(plan['sell_today_quintals']) else 'split'
        if kind not in groups or Decimal(plan['risk_adjusted_objective_inr'])>Decimal(groups[kind]['risk_adjusted_objective_inr']):groups[kind]=plan
    optimization['comparison_plans']=list(groups.values())
    for plan in (optimization.get('recommended_plan'),optimization.get('best_scenario_only_or_validated_plan')):
        if plan:plan['proposed_sale_date']=(datetime.fromisoformat(result['generated_at']).astimezone(ZoneInfo('Asia/Kolkata')).date()+timedelta(days=plan['holding_days'])).isoformat()
    result.update(inputs=body.model_dump(),reference_price_based=body.reference,scope='research_scenarios' if any(p['holding_days'] for p in optimization['feasible_plans']) else 'immediate_sale_only',holding_status='research_scenario_only' if options else 'missing_holding_assumptions' if missing else 'not_requested')
    if prior:
        result['changed_assumptions']=[k for k,v in body.model_dump().items() if prior.get('inputs',{}).get(k)!=v]
        result['previous_calculation']={'id':prior['id'],'generated_at':prior['generated_at'],'market_data':prior['market_data'],'selected_strategy':prior['selected_strategy']}
    return persist(db,result,parent)

@router.post('/api/v1/recommendations',response_model=PlannerResponse)
def recommend(body:Draft,db=Depends(get_db)):
    return from_draft(body,db)

@router.post('/api/v1/recommendations/{identifier}/recalculate-draft',response_model=PlannerResponse)
def recalculate_draft(identifier:str,body:Draft,x_plan_token:str|None=__import__('fastapi').Header(None),db=Depends(get_db)):
    return from_draft(body,db,identifier,x_plan_token)

@router.get('/api/v1/models/availability')
def models_available():
    import json
    from pathlib import Path
    registry=Path(__file__).resolve().parents[1]/'config/model-registry.json'
    entries=json.loads(registry.read_text()) if registry.exists() else []
    return {'generated_at':datetime.now(timezone.utc),'status':'research_artifacts_only','items':[{k:e[k] for k in ('version','commodity','market','variety','grade','horizon','candidate','trained_before','status')} for e in entries],'live_forecasts_available':False}

@router.get('/api/v1/forecasts')
def price_outlook(crop:str,market:str,variety:str,grade:str,horizon:int,db=Depends(get_db)):
    from .forecast_api import predict,PredictionRequest
    if horizon not in (1,3,7):raise HTTPException(422,{'status':'unsupported','code':'unsupported_horizon'})
    return predict(PredictionRequest(crop=crop,market=market,variety=variety,grade=grade,horizon=horizon),db)
