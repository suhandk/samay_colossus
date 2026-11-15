from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.db import Base,get_db
from backend.main import app
from backend.configure_catalog import Catalog
import pytest
@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def db():
        with Session(engine) as session: yield session
    app.dependency_overrides[get_db]=db
    with TestClient(app) as client: yield client
    app.dependency_overrides.clear()
def test_health(client):
    response=client.get('/api/health')
    assert response.json()=={'status':'ok'}
    assert response.headers['x-request-id']
def test_no_fabricated_data(client):
    data=client.get('/api/catalog').json()
    assert data['crops']==data['markets']==data['observed_pairs']==[]
    assert not data['ready']
def test_invalid_catalog():
    with pytest.raises(ValueError): Catalog.model_validate({'crops':[],'markets':[]})
def test_configurable_catalog():
    def entries(n): return [{'id':str(i),'names':{'en':'TEST ONLY','kn':'TEST ONLY'},'source_reference':'isolated fixture'} for i in range(n)]
    catalog=Catalog.model_validate({'crops':entries(4),'markets':entries(6)})
    assert len(catalog.crops)==4 and len(catalog.markets)==6
