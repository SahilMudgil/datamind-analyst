import pytest
import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, get_db
from main import app
from models.models import User, DatabaseConnection, SchemaCache, CSVUpload

TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply dependency override globally for tests
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function", autouse=True)
def setup_test_tables():
    """Create test tables cleanly before each test and tear down after each test."""
    Base.metadata.create_all(bind=test_engine, checkfirst=True)
    yield
    Base.metadata.drop_all(bind=test_engine, checkfirst=True)

@pytest.fixture
def db_session():
    """Yield a database session for direct test assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client():
    """Yield a FastAPI TestClient."""
    return TestClient(app)
