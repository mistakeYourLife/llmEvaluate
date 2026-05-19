from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from data.settings import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
