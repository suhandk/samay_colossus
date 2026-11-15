from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Numeric, CheckConstraint, UniqueConstraint
from .db import Base
class Crop(Base):
    __tablename__='crops'
    id=Column(String(80),primary_key=True)
    names=Column(JSON,nullable=False)
    source_reference=Column(String,nullable=False)
class Market(Base):
    __tablename__='markets'
    id=Column(String(80),primary_key=True)
    names=Column(JSON,nullable=False)
    source_reference=Column(String,nullable=False)
class Variety(Base):
    __tablename__='varieties'
    id=Column(String(80),primary_key=True)
    crop_id=Column(ForeignKey('crops.id'),nullable=False)
    name=Column(String,nullable=False)
class Grade(Base):
    __tablename__='grades'
    id=Column(String(80),primary_key=True)
    name=Column(String,nullable=False)
class DataSource(Base):
    __tablename__='data_sources'
    id=Column(String(80),primary_key=True)
    reference=Column(String,nullable=False)
class ImportHistory(Base):
    __tablename__='data_import_history'
    id=Column(Integer,primary_key=True)
    source_id=Column(ForeignKey('data_sources.id'),nullable=False)
    status=Column(String,nullable=False)
    details=Column(JSON,nullable=False)
    created_at=Column(DateTime(timezone=True),nullable=False)
class Observation(Base):
    __tablename__='market_observations'
    __table_args__=(CheckConstraint('price_inr_per_quintal > 0'),UniqueConstraint('source_id','source_record_id'))
    id=Column(Integer,primary_key=True)
    crop_id=Column(ForeignKey('crops.id'),nullable=False)
    market_id=Column(ForeignKey('markets.id'),nullable=False)
    variety_id=Column(ForeignKey('varieties.id'))
    grade_id=Column(ForeignKey('grades.id'))
    source_id=Column(ForeignKey('data_sources.id'),nullable=False)
    source_record_id=Column(String,nullable=False)
    observed_at=Column(DateTime(timezone=True),nullable=False)
    price_inr_per_quintal=Column(Numeric(14,2),nullable=False)
class ModelVersion(Base):
    __tablename__='model_versions'
    id=Column(String(80),primary_key=True)
    evidence=Column(JSON,nullable=False)
class Forecast(Base):
    __tablename__='forecasts'
    id=Column(Integer,primary_key=True)
    model_id=Column(ForeignKey('model_versions.id'),nullable=False)
    crop_id=Column(ForeignKey('crops.id'),nullable=False)
    market_id=Column(ForeignKey('markets.id'),nullable=False)
    generated_at=Column(DateTime(timezone=True),nullable=False)
    target_at=Column(DateTime(timezone=True),nullable=False)
    evidence=Column(JSON,nullable=False)
class FarmerProfile(Base):
    __tablename__='farmer_profiles'
    id=Column(String(80),primary_key=True)
    auth_subject=Column(String,unique=True,nullable=False)
    language=Column(String(5),nullable=False)
class SellingPlan(Base):
    __tablename__='selling_plans'
    id=Column(String(80),primary_key=True)
    farmer_id=Column(ForeignKey('farmer_profiles.id'))
    assumptions=Column(JSON,nullable=False)
    created_at=Column(DateTime(timezone=True),nullable=False)
class Calculation(Base):
    __tablename__='recommendation_calculations'
    id=Column(Integer,primary_key=True)
    plan_id=Column(ForeignKey('selling_plans.id'),nullable=False)
    engine_version=Column(String,nullable=False)
    evidence=Column(JSON,nullable=False)
class AppConfig(Base):
    __tablename__='application_configuration'
    key=Column(String(80),primary_key=True)
    value=Column(JSON,nullable=False)

from . import price_models
