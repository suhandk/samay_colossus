from sqlalchemy import Column,Integer,String,JSON,ForeignKey,DateTime,Numeric,Date,UniqueConstraint
from .schema_v1 import Base
class PriceImport(Base):
    __tablename__='price_imports'
    id=Column(Integer,primary_key=True)
    source_id=Column(ForeignKey('data_sources.id'),nullable=False)
    retrieved_at=Column(DateTime(timezone=True),nullable=False)
    imported_at=Column(DateTime(timezone=True),nullable=False)
    file_hash=Column(String(64),nullable=False)
    original_csv=Column(String,nullable=False)
    provenance=Column(JSON,nullable=False)
    counts=Column(JSON,nullable=False)
class PriceRecord(Base):
    __tablename__='price_records'
    __table_args__=(UniqueConstraint('identity_hash','record_hash'),)
    id=Column(Integer,primary_key=True)
    identity_hash=Column(String(64),nullable=False,index=True)
    record_hash=Column(String(64),nullable=False)
    import_id=Column(ForeignKey('price_imports.id'),nullable=False)
    source_id=Column(ForeignKey('data_sources.id'),nullable=False)
    crop_id=Column(ForeignKey('crops.id'),nullable=False)
    market_id=Column(ForeignKey('markets.id'),nullable=False)
    variety=Column(String,nullable=False)
    grade=Column(String,nullable=False)
    observation_date=Column(Date,nullable=False)
    minimum=Column(Numeric(16,4),nullable=False)
    modal=Column(Numeric(16,4),nullable=False)
    maximum=Column(Numeric(16,4),nullable=False)
    original_unit=Column(String,nullable=False)
    raw=Column(JSON,nullable=False)
    flags=Column(JSON,nullable=False)
    published_at=Column(DateTime(timezone=True))
    supersedes_id=Column(ForeignKey('price_records.id'))
class Quarantine(Base):
    __tablename__='price_quarantine'
    id=Column(Integer,primary_key=True)
    import_id=Column(ForeignKey('price_imports.id'),nullable=False)
    row_number=Column(Integer,nullable=False)
    raw=Column(JSON,nullable=False)
    reason=Column(String,nullable=False)
