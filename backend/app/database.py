from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.config import settings

# Determine connect args and normalize URL depending on backend dialect
db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif db_url.startswith("postgresql://"):
    # SQLAlchemy 2.0 defaults 'postgresql://' to psycopg (psycopg3).
    # Normalize to 'postgresql+psycopg2://' to ensure compatibility with psycopg2-binary.
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing an isolated database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
