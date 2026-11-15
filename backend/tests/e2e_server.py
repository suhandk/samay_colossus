"""Isolated test-only server. Never imports fixtures into an existing database."""
import os,sys,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
with tempfile.TemporaryDirectory(prefix='samay-e2e-') as directory:
    os.environ['DATABASE_URL']='sqlite:///'+(Path(directory)/'test.db').as_posix()
    from backend.db import Base,engine,Session
    from backend.models import Crop,Market,DataSource
    from backend.price_models import PriceImport,PriceRecord
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        for i in range(1,5):db.add(Crop(id='test-c'+str(i),names={'en':'TEST CROP '+str(i),'kn':'ಪರೀಕ್ಷಾ ಬೆಳೆ '+str(i)},source_reference='TEST ONLY'))
        for i in range(1,7):db.add(Market(id='test-m'+str(i),names={'en':'TEST MARKET '+str(i),'kn':'ಪರೀಕ್ಷಾ ಮಾರುಕಟ್ಟೆ '+str(i)},source_reference='TEST ONLY'))
        db.add(DataSource(id='test-source',reference='https://example.invalid/test-only'));db.flush()
        b=PriceImport(source_id='test-source',retrieved_at=datetime.now(timezone.utc),imported_at=datetime.now(timezone.utc),file_hash='TEST_ONLY',original_csv='TEST ONLY',provenance={'kind':'fixture'},counts={});db.add(b);db.flush()
        today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
        for i in range(3):db.add(PriceRecord(identity_hash='test'+str(i),record_hash='test'+str(i),import_id=b.id,source_id='test-source',crop_id='test-c1',market_id='test-m1' if i<2 else 'test-m2',variety='v',grade='g',observation_date=today-timedelta(days=i if i<2 else 30),minimum=900,modal=1000,maximum=1100,original_unit='INR/quintal',raw={'fixture':True},flags=[]))
    import uvicorn
    uvicorn.run('backend.main:app',host='127.0.0.1',port=8005)
