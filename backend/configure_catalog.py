import json,sys
from pydantic import BaseModel,Field,model_validator
from .db import Session
from .models import Crop,Market
from sqlalchemy import select
class Entry(BaseModel):
    id: str=Field(min_length=1,max_length=80)
    names: dict[str,str]
    source_reference: str=Field(min_length=1)
    @model_validator(mode='after')
    def languages(self):
        if not all(self.names.get(k,'').strip() for k in ('en','kn')): raise ValueError('Both languages required')
        return self
class Catalog(BaseModel):
    crops: list[Entry]=Field(min_length=4,max_length=4)
    markets: list[Entry]=Field(min_length=6,max_length=6)
    @model_validator(mode='after')
    def unique(self):
        for entries in (self.crops,self.markets):
            if len({e.id for e in entries})!=len(entries): raise ValueError('Duplicate IDs')
        return self
def configure(data):
    catalog=Catalog.model_validate(data)
    with Session.begin() as db:
        for cls,entries in ((Crop,catalog.crops),(Market,catalog.markets)):
            existing=set(db.scalars(select(cls.id)).all())
            incoming={e.id for e in entries}
            if existing-incoming: raise ValueError('Catalog replacement requires an explicit migration; existing records are preserved')
            for e in entries: db.merge(cls(**e.model_dump()))
if __name__=='__main__': configure(json.loads(open(sys.argv[1],encoding='utf-8').read()))
