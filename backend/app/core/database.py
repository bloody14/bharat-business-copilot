from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass

# Import model metadata before Alembic discovers Base.metadata.
from app.domain.inventory import models as inventory_models  # noqa: E402,F401
from app.domain.copilot import models as copilot_models  # noqa: E402,F401


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
