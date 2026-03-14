"""
conftest.py — pytest fixtures for all tests
Uses SQLite in-memory DB so no real PostgreSQL is needed in CI.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base, Startup, Investor, Investment

# ── SQLite in-memory test database ──────────────────────────────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_temp.db"

engine_test = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_test,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session, drop after."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def db_session(setup_database):
    """Provide a fresh DB session for each test; rolls back after."""
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def client(setup_database):
    """FastAPI TestClient that uses the in-memory DB."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def seeded_client(setup_database):
    """
    TestClient with pre-seeded data:
      - 1 Startup (id=1, name='TestStartup', country='USA')
      - 1 Investor (id=1, name='TestInvestor')
      - 1 Investment linking them (Seed, $500k)
    """
    app.dependency_overrides[get_db] = override_get_db

    # Seed once
    db = TestingSessionLocal()
    try:
        if db.query(Startup).count() == 0:
            startup = Startup(
                name="TestStartup",
                country="USA",
                description="A test startup",
                founded_year=2020,
                status="Active",
            )
            investor = Investor(
                name="TestInvestor",
                fund_name="Test Fund",
                focus_area="Technology",
            )
            db.add(startup)
            db.add(investor)
            db.flush()

            investment = Investment(
                startup_id=startup.id,
                investor_id=investor.id,
                round="Seed",
                amount_usd=500000.0,
                status="Active",
            )
            db.add(investment)
            db.commit()
    finally:
        db.close()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def auth_headers(seeded_client):
    """Return Authorization headers obtained from /token."""
    resp = seeded_client.post(
        "/token",
        data={"username": "admin", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
