import logging
from sqlalchemy import create_engine, event
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import Pool

from ..core.config import get_settings

settings = get_settings()

DB_POOL_SIZE = settings.db_pool_size
DB_MAX_OVERFLOW = settings.db_max_overflow
DB_POOL_RECYCLE = settings.db_pool_recycle
DB_POOL_TIMEOUT = settings.db_pool_timeout if hasattr(settings, 'db_pool_timeout') else 30
DB_ISOLATION_LEVEL = settings.db_isolation_level

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
    isolation_level=DB_ISOLATION_LEVEL,
    future=True,
    echo=settings.debug,
)

# Scoped session for thread safety
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
        future=True,
    )
)

Base = declarative_base()

# Enforce SQLite foreign keys
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
