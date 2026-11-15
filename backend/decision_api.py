"""Auditable API boundary; trusted scenarios are constructed only on the server."""
import hashlib,hmac,secrets
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,Header,HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field,model_validator
from sqlalchemy import select
from .db import get_db
from .models import Crop,Market,SellingPlan,Calculation,AppConfig
from .price_models import PriceRecord
from .prices_api import freshness,serialize
from .selling_engine import Input,SaleCosts,HoldingOption,PriceScenarios,Quantity,Nonnegative,Rate,Name,optimize_selling
from .forecast_service import forecast,ForecastUnavailable
router=APIRouter(prefix='/api/v1')
class KnownCosts(SaleCosts):
    fixed_transport_inr:Nonnegative
    fixed_transaction_inr:Nonnegative
    transport_inr_per_quintal:Nonnegative
    handling_inr_per_quintal:Nonnegative
    market_fee_rate:Rate
    commission_rate:Rate
class FutureOption(Input):
    days:int=Field(ge=1,le=7,strict=True)
    daily_loss_fractions:tuple[Rate,...]
    daily_storage_inr_per_quintal:tuple[Nonnegative,...]
    fixed_storage_inr:Nonnegative
    storage_payment:Literal['today','later']
    future_sale_costs:KnownCosts
    assumptions:Name
    sale_date_availability:Literal['confirmed','unknown']
    realization_multiplier:Decimal=Field(gt=0,le=2,decimal_places=6)
    adverse_price:Nonnegative
    # Explicit exploration prices are never called forecasts.
    user_future_price:Nonnegative|None=None
    @model_validator(mode='after')
    def schedules(self):
        if len(self.daily_loss_fractions)!=self.days or len(self.daily_storage_inr_per_quintal)!=self.days:raise ValueError('Supply every holding day explicitly')
        return self
class DecisionInput(Input):
    crop:str;market:str;variety:Name;grade:Name
    quantity:Quantity=Field(gt=0)
    buyer_price:Nonnegative|None=None
    reference_scenario:bool=False
    required_cash:Nonnegative
    cash_deadline:date
    storage:Literal['yes','no','unsure']
    storage_capacity:Quantity
    safe_holding_days:int=Field(ge=0,le=730,strict=True)
    storage_evidence:Name
    minimum_lot:Quantity=Field(gt=0)
    quantity_increment:Quantity=Field(gt=0)
    market_step:Quantity=Field(gt=0)
    today_costs:KnownCosts
    risk:Literal['conservative','balanced','aggressive']='conservative'
    holding_options:tuple[FutureOption,...]=()
    @model_validator(mode='after')
    def constraints(self):
        if self.storage!='yes' and (self.storage_capacity or self.holding_options):raise ValueError('Holding requires affirmative safe storage')
        if self.buyer_price is None and not self.reference_scenario:raise ValueError('Buyer quote required or explicitly select reference scenario')
        if self.buyer_price is not None and self.reference_scenario:raise ValueError('Choose buyer quote or reference scenario')
        if len(self.holding_options)>3:raise ValueError('At most three supported horizons')
        return self

def compute(body,db):
    now=datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('Asia/Kolkata')).date()
    if body.cash_deadline<today:raise HTTPException(422,{'code':'cash_deadline_passed'})
    crop=db.get(Crop,body.crop);market=db.get(Market,body.market)
    if not crop or not market:raise HTTPException(422,{'code':'unsupported_combination'})
    record=db.scalar(select(PriceRecord).where(PriceRecord.crop_id==body.crop,PriceRecord.market_id==body.market,PriceRecord.variety==body.variety,PriceRecord.grade==body.grade).order_by(PriceRecord.observation_date.desc(),PriceRecord.id.desc()))
    if not record:raise HTTPException(422,{'code':'unsupported_combination'})
    if body.reference_scenario and freshness(record.observation_date)!='current':raise HTTPException(409,{'code':'stale_reference'})
    price=record.modal if body.reference_scenario else body.buyer_price
    options=[];predictions=[];unresolved=[]
    for item in body.holding_options:
        if item.days not in (1,3,7):raise HTTPException(422,{'code':'unsupported_horizon'})
        if item.days>body.safe_holding_days:
            unresolved.append({'days':item.days,'code':'exceeds_safe_duration'});continue
        if item.sale_date_availability!='confirmed':
            unresolved.append({'days':item.days,'code':'unconfirmed_market_date'});continue
        if item.user_future_price is not None:
            central=item.user_future_price;lower=item.adverse_price;upper=central;version='user_scenario';flags=['user_entered_future_price_not_forecast'];source='Farmer assumption'
        else:
            try:p=forecast(db,body.crop,body.market,body.variety,body.grade,item.days)
            except (ForecastUnavailable,OSError,ValueError,ImportError):
                unresolved.append({'days':item.days,'code':'forecast_unavailable'});continue
            predictions.append(p)
            if not p['intervals']:
                unresolved.append({'days':item.days,'code':'uncertainty_unavailable'});continue
            band=max(p['intervals'],key=lambda b:b['nominal_level']);mult=item.realization_multiplier
            central=(Decimal(str(p['price']))*mult).quantize(Decimal('.01'));lower=(Decimal(str(band['lower']))*mult).quantize(Decimal('.01'));upper=(Decimal(str(band['upper']))*mult).quantize(Decimal('.01'));version=p['model_version'];flags=p['flags'];source='Saved research forecast plus farmer realization assumption'
        scenario=PriceScenarios(adverse_inr_per_quintal=item.adverse_price,lower_inr_per_quintal=lower,central_inr_per_quintal=central,upper_inr_per_quintal=upper,reliability_status='scenario only',market=market.names['en'],commodity=crop.names['en'],variety=body.variety,grade=body.grade,target_date=today+timedelta(days=item.days),issued_at=now,model_version=version,source=source,price_basis_assumption='Explicit future buyer quote or farmer mandi-realization multiplier',adverse_assumption='Farmer-supplied adverse price',flags=tuple(flags))
        options.append(HoldingOption(**item.model_dump(exclude={'sale_date_availability','realization_multiplier','adverse_price','user_future_price'}),scenarios=scenario))
    request=dict(commodity=crop.names['en'],market=market.names['en'],variety=body.variety,grade=body.grade,decision_at=now,total_quantity_quintals=body.quantity,today_price_inr_per_quintal=price,today_price_assumption='Reference scenario only; buyer confirmation needed' if body.reference_scenario else 'Farmer buyer quote',required_net_cash_inr=body.required_cash,storage_capacity_quintals=body.storage_capacity,decision_increment_quintals=body.quantity_increment,market_quantity_step_quintals=body.market_step,minimum_sale_lot_quintals=body.minimum_lot,maximum_horizon_days=body.safe_holding_days,crop_storage_profile={'commodity':crop.names['en'],'maximum_holding_days':body.safe_holding_days,'storage_conditions':body.storage_evidence,'assumption_source':'Farmer provided, not independently verified'},today_sale_costs=body.today_costs,holding_options=tuple(options),risk_tolerance=body.risk)
    try:result=optimize_selling(request)
    except ValueError as error:raise HTTPException(422,{'code':'invalid_financial_or_quantity_constraints','reason':str(error)})
    chosen=result['recommended_plan'];candidate=result['best_scenario_only_or_validated_plan']
    if body.reference_scenario:unresolved.append({'code':'buyer_quote_needed_for_confirmed_cash_feasibility'})
    if body.holding_options and not options:unresolved.append({'code':'holding_not_evaluated'})
    return jsonable_encoder({'id':str(uuid4()),'generated_at':now,'input_assumptions':body.model_dump(),'engine_input':result['request_and_assumptions'],'engine_version':'samay-selling-v1','selected_strategy':chosen,'conditional_exploration':candidate if candidate and not candidate['recommendation_eligible'] else None,'optimization':result,'feasibility_status':'reference_scenario_only' if body.reference_scenario else 'no_feasible_plan' if not chosen and not candidate else 'partial_evaluation' if unresolved else 'feasible','confirmed_cash_feasibility':not body.reference_scenario and chosen is not None,'market_data':serialize(db,record),'predictions':predictions,'unresolved_assumptions':unresolved,'explanation':{'cash_constraint':str(body.required_cash),'cash_deadline':body.cash_deadline.isoformat(),'cash_policy':'Today cash must meet the requirement even for a later deadline; future receipts are not guaranteed','safe_storage_evidence':body.storage_evidence,'risk_formula':{'conservative':'adverse','balanced':'0.5 central + 0.5 adverse','aggressive':'0.8 central + 0.2 adverse'}[body.risk],'break_even_basis':'Whole-harvest net equivalence against sell-all-now, preserving fixed-cost interactions','en':'No feasible selling plan currently satisfies your requirements.' if not candidate else 'Cash and physical constraints are enforced. Holding scenarios remain conditional on the recorded assumptions.','kn':'ನಿಮ್ಮ ಅಗತ್ಯಗಳನ್ನು ಪೂರೈಸುವ ಸಾಧ್ಯವಾದ ಮಾರಾಟ ಯೋಜನೆ ಈಗ ಲಭ್ಯವಿಲ್ಲ.' if not candidate else 'ಹಣ ಮತ್ತು ಸಂಗ್ರಹ ಮಿತಿಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗಿದೆ. ಸಂಗ್ರಹದ ಫಲಿತಾಂಶ ದಾಖಲಿಸಿದ ಅಂದಾಜುಗಳನ್ನು ಅವಲಂಬಿಸಿದೆ.'}},custom_encoder={Decimal:str})

def persist(db,payload,parent=None):
    token=secrets.token_urlsafe(32)
    db.add(SellingPlan(id=payload['id'],farmer_id=None,assumptions=payload['input_assumptions'],created_at=datetime.now(timezone.utc)));db.flush()
    if parent:payload['previous_recommendation_id']=parent
    db.add(Calculation(plan_id=payload['id'],engine_version=payload['engine_version'],evidence=payload))
    db.add(AppConfig(key='decision:'+payload['id'],value={'token_hash':hashlib.sha256(token.encode()).hexdigest()}));db.commit()
    return {**payload,'access_token':token}

def read(db,identifier,token):
    config=db.get(AppConfig,'decision:'+identifier)
    if not token or not config or not hmac.compare_digest(config.value['token_hash'],hashlib.sha256(token.encode()).hexdigest()):raise HTTPException(404,'Recommendation not found')
    calculation=db.scalar(select(Calculation).where(Calculation.plan_id==identifier))
    if not calculation:raise HTTPException(404,'Recommendation not found')
    return calculation.evidence
@router.post('/recommend')
def recommend(body:DecisionInput,db=Depends(get_db)):
    try:return persist(db,compute(body,db))
    except ValueError as error:raise HTTPException(422,{'code':'invalid_scenario','reason':str(error)})
@router.post('/recommendations/compare')
def compare(body:DecisionInput,db=Depends(get_db)):
    return recommend(body,db)
@router.get('/recommendations/{identifier}')
def get_recommendation(identifier:str,x_plan_token:str|None=Header(None),db=Depends(get_db)):
    return read(db,identifier,x_plan_token)
@router.post('/recommendations/{identifier}/recalculate')
def recalculate(identifier:str,body:DecisionInput,x_plan_token:str|None=Header(None),db=Depends(get_db)):
    read(db,identifier,x_plan_token)
    try:return persist(db,compute(body,db),identifier)
    except ValueError as error:raise HTTPException(422,{'code':'invalid_scenario','reason':str(error)})
