import json, logging, time, uuid
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from .db import get_db, settings
from .models import Crop, Market, Observation
logging.basicConfig(level=logging.INFO, format='%(message)s')
log=logging.getLogger('samay')
app=FastAPI(title='SAMAY',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Plan-Token'])
@app.middleware('http')
async def logging_middleware(request,call_next):
    rid=str(uuid.uuid4()); start=time.monotonic()
    try: response=await call_next(request)
    except Exception:
        log.exception(json.dumps({'event':'request_failed','request_id':rid}))
        response=JSONResponse(status_code=500,content={'detail':'Internal server error','request_id':rid})
    response.headers['X-Request-ID']=rid
    log.info(json.dumps({'request_id':rid,'status':response.status_code,'duration_ms':round((time.monotonic()-start)*1000)}))
    return response
@app.get('/api/health')
def health(db=Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status':'ok'}
@app.get('/api/catalog')
def catalog(db=Depends(get_db)):
    crops=db.scalars(select(Crop)).all(); markets=db.scalars(select(Market)).all()
    from .price_models import PriceRecord
    pairs=db.execute(select(PriceRecord.crop_id,PriceRecord.market_id).distinct()).all()
    return {'crops':[{'id':c.id,'names':c.names} for c in crops],'markets':[{'id':m.id,'names':m.names} for m in markets],'observed_pairs':[{'crop_id':c,'market_id':m} for c,m in pairs],'ready':len(crops)==4 and len(markets)==6}

from .prices_api import router
app.include_router(router)

from .recommendations import router as recommendation_router
app.include_router(recommendation_router)

from .forecast_api import router as forecast_router
app.include_router(forecast_router)

from .decision_api import router as decision_router
app.include_router(decision_router)
