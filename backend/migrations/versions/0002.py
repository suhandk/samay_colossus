from alembic import op
from backend.migrations.price_schema_v2 import PriceImport,PriceRecord,Quarantine
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    for model in (PriceImport,PriceRecord,Quarantine): model.__table__.create(op.get_bind())
def downgrade():
    for model in (Quarantine,PriceRecord,PriceImport): model.__table__.drop(op.get_bind())
