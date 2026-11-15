import json
from pathlib import Path
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from .db import get_db
from .forecast_service import forecast,ForecastUnavailable
router=APIRouter(prefix='/api/v1')
class PredictionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    crop:str;market:str;variety:str;grade:str;horizon:int=Field(ge=1,le=7,strict=True)
@router.post('/predict')
def predict(body:PredictionRequest,db=Depends(get_db)):
    if body.horizon not in (1,3,7):raise HTTPException(422,{'status':'unsupported','code':'unsupported_horizon'})
    try:return forecast(db,body.crop,body.market,body.variety,body.grade,body.horizon)
    except ForecastUnavailable as error:
        code=str(error);status='stale data' if code=='stale_market_data' else 'unsupported' if code.startswith('unsupported') else 'unavailable'
        raise HTTPException(503 if status!='unsupported' else 422,{'status':status,'code':code,'generated_at':datetime.now(timezone.utc).isoformat()})
    except (OSError,ValueError,ImportError):raise HTTPException(503,{'status':'unavailable','code':'forecast_artifact_unavailable'})
@router.get('/models/status')
def status():
    root=Path(__file__).resolve().parents[1];path=root/'models/evaluated/report.json';reports=json.loads(path.read_text()) if path.exists() else []
    return {'generated_at':datetime.now(timezone.utc),'evaluations':reports,'promotion_policy':'Explicit offline evaluation and promotion required; no request-time training','reliability':'limited evidence','limitations':['Historical publication times unknown','Research evaluation does not validate buyer sale prices']}
