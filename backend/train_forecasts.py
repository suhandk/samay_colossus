"""Explicit offline chronological model evaluation; never called during inference."""
import argparse,hashlib,json,pickle,platform
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np
import pandas as pd
from sqlalchemy import select
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
from .db import Session
from .models import Crop,Market
from .price_models import PriceRecord,PriceImport
from .model_math import FEATURES
SEED=42

def metrics(y,p,last):
    y,p,last=map(lambda a:np.asarray(a,dtype=float),(y,p,last));den=np.abs(y)+np.abs(p)
    return {'n':len(y),'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),'wape_pct':float(100*np.abs(y-p).sum()/np.abs(y).sum()) if np.abs(y).sum() else None,'smape_pct':float(np.mean(np.divide(200*np.abs(y-p),den,out=np.zeros_like(den),where=den>0))),'directional_accuracy':float(np.mean(np.sign(y-last)==np.sign(p-last)))}
def feature_rows(series,horizon):
    values=series['modal'].to_numpy(float);dates=series['date'].tolist();targets=dict(zip(dates,values));rows=[]
    for i in range(30,len(values)):
        origin=dates[i];history=values[:i];target=origin+timedelta(days=horizon)
        if target not in targets:continue
        f={f'lag_{n}_obs_inr_per_quintal':float(history[-n]) for n in (1,2,3,7,14,30)}
        for n in (7,14,30):
            for name,fn in [('mean',np.mean),('median',np.median),('std',lambda a:np.std(a,ddof=1))]:f[f'rolling_{name}_{n}_obs_inr_per_quintal']=float(fn(history[-n:]))
        f.update(origin_weekday=origin.weekday(),origin_month=origin.month,target_weekday=target.weekday(),target_month=target.month,days_since_latest_report=(origin-dates[i-1]).days,history_30_obs_span_days=(dates[i-1]-dates[i-30]).days)
        # Only information with report date strictly before origin enters features.
        if f['days_since_latest_report']>3:continue
        seasonal=targets.get(target-timedelta(days=7)) if target-timedelta(days=7)<origin else None
        rows.append({**f,'origin':origin,'target':target,'y':targets[target],'seasonal':seasonal})
    return pd.DataFrame(rows)
def candidates(n):
    result={'last':None,'mean14':None,'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10)),'hist_gradient_boosting':HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=7,l2_regularization=10,random_state=SEED)}
    if n>=500:
        from lightgbm import LGBMRegressor
        result['lightgbm']=LGBMRegressor(n_estimators=100,num_leaves=7,random_state=SEED,n_jobs=1,verbosity=-1)
    return result
def predict(name,model,frame):
    if name=='last':return frame.lag_1_obs_inr_per_quintal.to_numpy()
    if name=='mean14':return frame.rolling_mean_14_obs_inr_per_quintal.to_numpy()
    if name=='seasonal':return frame.seasonal.to_numpy(float)
    return np.maximum(0,model.predict(frame[FEATURES]))
def evaluate(series,horizon,out,scope):
    frame=feature_rows(series,horizon)
    report={'scope':scope,'horizon':horizon,'raw_observations':len(series),'eligible_origins':len(frame),'status':'insufficient_history','limitations':['Retrospective snapshot evaluation: original publication/revision times are unknown','Missing dates are not imputed; closures cannot be inferred from gaps','Intervals describe mandi reference prices, not buyer realization'],'inspection':{'first':str(series.date.min()),'last':str(series.date.max()),'missing_calendar_days':(series.date.max()-series.date.min()).days+1-len(series),'duplicate_dates':int(series.date.duplicated().sum()),'price_change_over_50pct':int((series.modal.pct_change().abs()>.5).sum()),'monthly_observation_counts':series.groupby(series.date.map(lambda d:d.month)).size().to_dict(),'seasonality':'Monthly counts are descriptive; insufficient multiple-year evidence for seasonal claims'}}
    if len(frame)<120:return report
    n=len(frame);boundaries=[int(n*.55),int(n*.70),int(n*.85)]
    segments=[frame.iloc[:boundaries[0]],frame.iloc[boundaries[0]:boundaries[1]],frame.iloc[boundaries[1]:boundaries[2]],frame.iloc[boundaries[2]:]]
    train,validation,calibration,holdout=[segment[segment.target<next_start] if next_start is not None else segment for segment,next_start in zip(segments,[s.origin.iloc[0] for s in segments[1:]]+[None])]
    if min(map(len,(validation,calibration,holdout)))<15 or len(train)<60:return report
    models=candidates(len(train))
    if frame.seasonal.notna().all():models['seasonal']=None
    comparisons={};fitted={}
    for name,model in models.items():
        if model is not None:model.fit(train[FEATURES],train.y)
        fitted[name]=model
        comparisons[name]=metrics(validation.y,predict(name,model,validation),validation.lag_1_obs_inr_per_quintal)
    winner=min(comparisons,key=lambda name:(comparisons[name]['mae'],name))
    # Winner and preprocessing are now frozen; calibration cannot select a model.
    model=fitted[winner];cal_predictions=predict(winner,model,calibration);errors=np.abs(calibration.y.to_numpy()-cal_predictions)
    radius=float(np.quantile(errors,.9,method='higher')) if len(errors)>=30 else None
    hp=predict(winner,model,holdout);held=metrics(holdout.y,hp,holdout.lag_1_obs_inr_per_quintal)
    coverage=float(np.mean((holdout.y>=np.maximum(0,hp-radius))&(holdout.y<=hp+radius))) if radius is not None else None
    # Rolling-origin diagnostics use earlier train prefixes, not holdout rows.
    folds=[]
    for fraction in (.65,.8):
        cutoff=int(len(train)*fraction);prefix=train.iloc[:cutoff];next_rows=train.iloc[cutoff:cutoff+15];prefix=prefix[prefix.target<next_rows.origin.iloc[0]]
        if len(prefix)<30:continue
        candidate=candidates(len(prefix)).get(winner)
        if candidate is not None:candidate.fit(prefix[FEATURES],prefix.y)
        folds.append(metrics(next_rows.y,predict(winner,candidate,next_rows),next_rows.lag_1_obs_inr_per_quintal))
    fingerprint=hashlib.sha256(series.to_json(date_format='iso').encode()).hexdigest();version=hashlib.sha256((json.dumps(scope,sort_keys=True)+str(horizon)+fingerprint+winner).encode()).hexdigest()[:20]
    folder=out/version;folder.mkdir(parents=True,exist_ok=True);payload=pickle.dumps(model);(folder/'model.pkl').write_bytes(payload)
    report.update(status='evaluated_research_only',candidate=winner,validation_comparison=comparisons,holdout=held,holdout_baseline=metrics(holdout.y,holdout.lag_1_obs_inr_per_quintal,holdout.lag_1_obs_inr_per_quintal),calibration={'n':len(calibration),'nominal_level':.9,'radius':radius,'holdout_coverage':coverage,'availability':'available' if radius is not None else 'unavailable_under_30_calibration_samples'},rolling_origin=folds,partitions={name:{'n':len(s),'origins':[str(s.origin.min()),str(s.origin.max())],'targets':[str(s.target.min()),str(s.target.max())]} for name,s in zip(('train','validation','calibration','holdout'),(train,validation,calibration,holdout))},version=version,feature_schema=FEATURES,source_fingerprint=fingerprint,model_sha256=hashlib.sha256(payload).hexdigest(),trained_at=datetime.now(timezone.utc).isoformat(),seed=SEED,python=platform.python_version(),promotion='not_promoted')
    (folder/'evaluation.json').write_text(json.dumps(report,indent=2,default=str));return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('models/evaluated'));args=parser.parse_args();reports=[]
    with Session() as db:
        rows=db.execute(select(PriceRecord,PriceImport).join(PriceImport,PriceRecord.import_id==PriceImport.id)).all();groups={}
        for r,b in rows:
            if b.provenance.get('data_kind')!='official':continue
            key=(r.crop_id,r.market_id,r.variety,r.grade);groups.setdefault(key,[]).append((r,b))
        for key,records in sorted(groups.items()):
            # Preserve latest revision, reject conflicts from independent imports.
            prices={};hashes=set()
            for r,b in records:
                if b.file_hash not in hashes and hashlib.sha256(b.original_csv.encode()).hexdigest()!=b.file_hash:raise ValueError('Source hash mismatch')
                hashes.add(b.file_hash)
                if r.observation_date in prices and prices[r.observation_date]!=float(r.modal):raise ValueError('Conflicting series vintages require explicit revision resolution')
                prices[r.observation_date]=float(r.modal)
            series=pd.DataFrame([{'date':d,'modal':v} for d,v in sorted(prices.items())]);scope=dict(zip(('crop','market','variety','grade'),key))
            for horizon in (1,3,7):
                report=evaluate(series,horizon,args.output,scope);report['source_hashes']=sorted(hashes)
                if report.get('version'):(args.output/report['version']/'evaluation.json').write_text(json.dumps(report,indent=2,default=str))
                reports.append(report)
    args.output.mkdir(parents=True,exist_ok=True);(args.output/'report.json').write_text(json.dumps(reports,indent=2,default=str))
    print(json.dumps({'series':len(groups),'evaluations':len(reports),'evaluated':sum(r['status']=='evaluated_research_only' for r in reports),'report':str(args.output/'report.json')}))
if __name__=='__main__':main()
