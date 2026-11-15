"""Hash-pinned inference using supplied feature math; never synthesizes uncertainty."""
import hashlib,json,pickle
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from .models import Crop,Market
from .price_models import PriceRecord,PriceImport
ROOT=Path(__file__).resolve().parents[1]
class ForecastUnavailable(ValueError):pass

def forecast(db,crop_id,market_id,variety,grade,horizon):
    import numpy as np
    import pandas as pd
    from .model_math import FEATURES,features_at,predict_rows,seasonal_value
    if type(horizon) is not int or horizon not in (1,3,7):raise ForecastUnavailable('unsupported_horizon')
    now=datetime.now(timezone.utc);origin=now.astimezone(ZoneInfo('Asia/Kolkata')).date()
    c=db.get(Crop,crop_id);m=db.get(Market,market_id)
    if not c or not m:raise ForecastUnavailable('unsupported_series')
    registry=json.loads((ROOT/'config/model-registry.json').read_text())
    entry=next((e for e in registry if (e['commodity'],e['market'],e['variety'],e['grade'],e['horizon'])==(c.names['en'],m.names['en'],variety,grade,horizon)),None)
    if not entry:raise ForecastUnavailable('unsupported_horizon')
    folder=ROOT/entry['directory'];raw=(folder/'metadata.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=entry['metadata_sha256']:raise ForecastUnavailable('metadata_integrity')
    meta=json.loads(raw)
    report=(ROOT/'models/evidence'/meta['selection_report_sha256']).read_bytes()
    if hashlib.sha256(report).hexdigest()!=meta['selection_report_sha256'] or meta['feature_schema']!=FEATURES:raise ForecastUnavailable('evidence_integrity')
    if datetime.fromisoformat(meta['trained_before'])>now:raise ForecastUnavailable('future_artifact')
    rows=db.execute(select(PriceRecord,PriceImport).join(PriceImport,PriceRecord.import_id==PriceImport.id).where(PriceRecord.crop_id==crop_id,PriceRecord.market_id==market_id,PriceRecord.variety==variety,PriceRecord.grade==grade)).all()
    vintages=[];checked=set()
    for r,b in rows:
        if b.provenance.get('data_kind')!='official':continue
        if b.id not in checked:
            if hashlib.sha256(b.original_csv.encode('utf-8')).hexdigest()!=b.file_hash:raise ForecastUnavailable('source_integrity')
            checked.add(b.id)
        available=b.retrieved_at.replace(tzinfo=timezone.utc) if b.retrieved_at.tzinfo is None else b.retrieved_at
        vintages.append({'report_date':r.observation_date,'available_at':pd.Timestamp(available),'price':float(r.modal),'batch_id':b.id,'row_id':r.id,'file_sha256':b.file_hash})
    if not vintages:raise ForecastUnavailable('missing_history')
    frame=pd.DataFrame(vintages);features,audit=features_at(frame,origin,horizon,decision_at=now)
    if not np.isfinite(list(features.values())).all():raise ForecastUnavailable('insufficient_history')
    if features['days_since_latest_report']>1:raise ForecastUnavailable('stale_market_data')
    model_bytes=(folder/'model.pkl').read_bytes()
    if hashlib.sha256(model_bytes).hexdigest()!=entry['model_sha256']:raise ForecastUnavailable('model_integrity')
    model=pickle.loads(model_bytes)
    feature_frame=pd.DataFrame([{**features,'seasonal_price':seasonal_value(frame,origin,horizon)}])
    price=float(predict_rows(meta['candidate'],model,feature_frame)[0])
    intervals=[{'nominal_level':float(level),'lower':max(0,price-radius),'upper':price+radius} for level,radius in meta.get('empirical_calibration',{}).get('radii',{}).items()]
    return {'price':price,'intervals':intervals,'target_date':(origin+timedelta(days=horizon)).isoformat(),'generated_at':now.isoformat(),'model_version':entry['version'],'reliability':'limited_evidence','flags':['research_only','historical_publication_unverified'],'audit':audit,'crop':crop_id,'market':market_id,'variety':variety,'grade':grade,'predicted_modal_price_inr_per_quintal':price,'training_cutoff':meta.get('training_window',[None,None])[-1],'last_observed_price_date':audit['max_feature_report_date'],'data_source':{'kind':'official','file_hashes':sorted({v['file_sha256'] for v in vintages})},'limitations':['Research evidence only','Historical publication times unknown','Intervals do not guarantee farmer realization'],'explanation':{'en':'This estimate uses saved historical evidence. Future mandi prices and buyer offers remain uncertain.','kn':'ಈ ಅಂದಾಜು ಉಳಿಸಿದ ಇತಿಹಾಸದ ಮಾಹಿತಿಯನ್ನು ಬಳಸುತ್ತದೆ. ಭವಿಷ್ಯದ ಮಂಡಿ ಬೆಲೆ ಮತ್ತು ಖರೀದಿದಾರರ ಬೆಲೆ ಅನಿಶ್ಚಿತ.'}}
