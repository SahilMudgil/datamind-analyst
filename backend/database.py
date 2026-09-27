from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# Create engine for Application Database (pgvector + metadata, with SQLite local fallback support)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency to yield database sessions with clean teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
