from datetime import date,timedelta
import numpy as np
import pandas as pd
from backend.train_forecasts import feature_rows,evaluate,metrics
from backend.tests.test_foundation import client

def test_causal_features_and_exact_target():
    series=pd.DataFrame({'date':[date(2020,1,1)+timedelta(days=i) for i in range(80)],'modal':np.arange(80)+100.})
    first=feature_rows(series,3);changed=series.copy();changed.loc[40:,'modal']=9999
    second=feature_rows(changed,3)
    columns=[c for c in first if c not in ('y','seasonal')]
    pd.testing.assert_frame_equal(first[first.origin<date(2020,2,10)][columns],second[second.origin<date(2020,2,10)][columns])
    assert all(t-o==timedelta(days=3) for t,o in zip(first.target,first.origin))

def test_metrics_not_accuracy():
    result=metrics([100,200],[110,180],[90,190]);assert result['mae']==15;assert result['wape_pct']==10

def test_insufficient_history(tmp_path):
    s=pd.DataFrame({'date':[date(2020,1,1)+timedelta(days=i) for i in range(40)],'modal':[100.]*40})
    assert evaluate(s,7,tmp_path,{})['status']=='insufficient_history'

def test_prediction_api_validation(client):
    assert client.post('/api/v1/predict',json={'crop':'c','market':'m','variety':'v','grade':'g','horizon':2}).status_code==422
    response=client.post('/api/v1/predict',json={'crop':'missing','market':'m','variety':'v','grade':'g','horizon':1})
    assert response.status_code==422
    assert client.get('/api/v1/models/status').status_code==200
