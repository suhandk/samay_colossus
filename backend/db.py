from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
class Settings(BaseSettings):
    database_url: str = 'sqlite:///./samay.db'
    cors_origins: str = 'http://localhost:5173'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
settings = Settings()
class Base(DeclarativeBase): pass
engine = create_engine(settings.database_url)
if engine.dialect.name == 'sqlite':
    @event.listens_for(engine, 'connect')
    def sqlite_foreign_keys(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine)
def get_db():
    with Session() as db: yield db
