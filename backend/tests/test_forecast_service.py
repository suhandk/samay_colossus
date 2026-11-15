import json,pickle,hashlib
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.db import Base
from backend.models import Crop,Market,DataSource
from backend.price_models import PriceImport,PriceRecord
from backend import forecast_service as service
from backend.model_math import FEATURES
import pytest

def test_inference_and_stale_gate(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'ROOT',tmp_path)
    folder=tmp_path/'models/test';folder.mkdir(parents=True);(tmp_path/'config').mkdir();(tmp_path/'models/evidence').mkdir()
    model=pickle.dumps(None);report=b'TEST ONLY';report_hash=hashlib.sha256(report).hexdigest();(tmp_path/'models/evidence'/report_hash).write_bytes(report)
    now=datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('Asia/Kolkata')).date()
    meta={'feature_schema':FEATURES,'selection_report_sha256':report_hash,'trained_before':(now-timedelta(days=2)).isoformat(),'candidate':'naive','empirical_calibration':{'radii':{'.9':10}}}
    raw=json.dumps(meta).encode();(folder/'metadata.json').write_bytes(raw);(folder/'model.pkl').write_bytes(model)
    (tmp_path/'config/model-registry.json').write_text(json.dumps([{'commodity':'TEST','market':'TEST','variety':'v','grade':'g','horizon':1,'directory':'models/test','metadata_sha256':hashlib.sha256(raw).hexdigest(),'model_sha256':hashlib.sha256(model).hexdigest(),'version':'TEST ONLY'}]))
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Crop(id='c',names={'en':'TEST'},source_reference='fixture'),Market(id='m',names={'en':'TEST'},source_reference='fixture'),DataSource(id='s',reference='fixture')]);db.flush()
        b=PriceImport(source_id='s',retrieved_at=now-timedelta(hours=1),imported_at=now,file_hash=hashlib.sha256(b'TEST ONLY').hexdigest(),original_csv='TEST ONLY',provenance={'data_kind':'official'},counts={});db.add(b);db.flush()
        for i in range(1,36):db.add(PriceRecord(identity_hash=str(i),record_hash=str(i),import_id=b.id,source_id='s',crop_id='c',market_id='m',variety='v',grade='g',observation_date=today-timedelta(days=i),minimum=900,modal=1000,maximum=1100,original_unit='INR/quintal',raw={},flags=[]))
        db.flush();result=service.forecast(db,'c','m','v','g',1)
        assert result['price']==1000 and result['reliability']=='limited_evidence'
        assert result['intervals'][0]['lower']==990
        db.query(PriceRecord).filter(PriceRecord.observation_date>=today-timedelta(days=1)).delete();db.flush()
        with pytest.raises(service.ForecastUnavailable,match='stale_market_data'):service.forecast(db,'c','m','v','g',1)
        with pytest.raises(service.ForecastUnavailable,match='unsupported_horizon'):service.forecast(db,'c','m','other','g',1)
