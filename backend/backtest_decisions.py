"""Chronological persistence-scenario research; strict as-of never assumes publication dates."""
import argparse,json
from pathlib import Path
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal
from statistics import mean,median
from sqlalchemy import select
from .db import Session
from .models import Crop,Market
from .price_models import PriceRecord,PriceImport
from .selling_engine import optimize_selling,sale

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,default=Path('reports/decision-backtest.json'));args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text());reports=[]
    with Session() as db:
        rows=db.execute(select(PriceRecord,PriceImport).join(PriceImport,PriceRecord.import_id==PriceImport.id)).all();groups={}
        for r,b in rows:
            if b.provenance.get('data_kind')=='official':groups.setdefault((r.crop_id,r.market_id,r.variety,r.grade),[]).append((r,b))
        for scope,records in sorted(groups.items()):
            prices={r.observation_date:r.modal for r,b in records};dates=sorted(prices);samples=[];strict_count=0;attempted=0;infeasible=0
            for origin in dates[30::7]:
                target=origin+timedelta(days=3)
                if target not in prices:continue
                history=[d for d in dates if d<origin]
                if not history:continue
                # Current origin buyer quote and all costs are evaluation assumptions.
                current=prices[origin];central=prices[history[-1]];adverse=min(prices[d] for d in history[-30:])
                observed=[(r,b) for r,b in records if r.observation_date<origin and b.retrieved_at.date()<=origin]
                if len(observed)>=30:strict_count+=1
                crop=db.get(Crop,scope[0]).names['en'];market=db.get(Market,scope[1]).names['en']
                costs=protocol['sale_costs'];q=protocol['quantity'];cash=protocol['required_cash'];days=3
                request=dict(commodity=crop,market=market,variety=scope[2],grade=scope[3],decision_at=datetime.combine(origin,time(12),timezone.utc),total_quantity_quintals=q,today_price_inr_per_quintal=str(current),today_price_assumption='Research assumption: buyer realizes dated modal exactly',required_net_cash_inr=cash,storage_capacity_quintals=protocol['storage_capacity'],decision_increment_quintals=protocol['quantity_increment'],market_quantity_step_quintals=protocol['market_step'],minimum_sale_lot_quintals=protocol['minimum_lot'],maximum_horizon_days=3,crop_storage_profile={'commodity':crop,'maximum_holding_days':3,'storage_conditions':'Research protocol, not verified crop shelf life','assumption_source':str(args.protocol)},today_sale_costs=costs,risk_tolerance=protocol['risk'],holding_options=[{'days':3,'daily_loss_fractions':[protocol['daily_loss']]*3,'daily_storage_inr_per_quintal':[protocol['daily_storage']]*3,'fixed_storage_inr':protocol['fixed_storage'],'storage_payment':protocol['storage_payment'],'future_sale_costs':costs,'assumptions':'Predeclared research protocol','scenarios':{'adverse_inr_per_quintal':str(adverse),'lower_inr_per_quintal':str(adverse),'central_inr_per_quintal':str(central),'upper_inr_per_quintal':str(central),'reliability_status':'scenario only','market':market,'commodity':crop,'variety':scope[2],'grade':scope[3],'target_date':target,'issued_at':datetime.combine(origin,time(12),timezone.utc),'model_version':'historical_persistence_scenario','source':'Prior observed price; not a trained forecast','price_basis_assumption':'Research full modal realization','adverse_assumption':'Prior 30-observation minimum; explicit stress assumption','flags':['retrospective_snapshot']}}])
                attempted+=1
                result=optimize_selling(request);plan=result['best_scenario_only_or_validated_plan']
                if not plan:
                    infeasible+=1;continue
                from .selling_engine import SaleCosts
                future=sale(plan['later_saleable_quintals'],prices[target],SaleCosts.model_validate(costs))
                realized=plan['cash_today_inr']+future['net_inr']-plan['storage_paid_later_inr'];baseline=result['sell_all_now']['sale']['net_inr']
                samples.append({'origin':origin.isoformat(),'target':target.isoformat(),'net_difference':str(realized-baseline),'cash_success':plan['cash_today_inr']>=Decimal(cash),'hold_quantity':str(plan['hold_initial_quintals'])})
            gains=[Decimal(s['net_difference']) for s in samples]
            reports.append({'scope':scope,'research_n':len(samples),'attempted_origins':attempted,'infeasible_origins':infeasible,'strict_asof_eligible_origins':strict_count,'mean_net_gain':str(mean(gains)) if gains else None,'median_net_gain':str(median(gains)) if gains else None,'periods_won_fraction':sum(g>0 for g in gains)/len(gains) if gains else None,'worst_net_difference':str(min(gains)) if gains else None,'cash_success_fraction':sum(s['cash_success'] for s in samples)/len(samples) if samples else None,'samples':samples})
    payload={'protocol':protocol,'evaluation_kind':'retrospective_snapshot_research','strict_asof_results':'Unavailable: no original historical publication vintages or historical buyer quotes; no strict performance claim','limitations':['Assumed realization equals modal; not actual farmer transactions','Storage safety/loss/costs are protocol assumptions, not agronomic facts','Historical persistence scenario is not evaluation of the newly trained forecasting champions','No claim of additional farmer income','Feasible-origin results exclude no-feasible-plan periods; see source sample limitations'],'series':reports}
    args.output.parent.mkdir(exist_ok=True);args.output.write_text(json.dumps(payload,indent=2));print(json.dumps({'series':len(reports),'research_samples':sum(r['research_n'] for r in reports),'output':str(args.output)}))
if __name__=='__main__':main()
