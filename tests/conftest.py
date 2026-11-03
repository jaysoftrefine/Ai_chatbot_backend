import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ["APP_ENV"] = "testing"

from app.core.config import settings
from app.db.base import Base
import app.db.models  # ensure models are loaded
from app.db.session import get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user_a(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert reg.status_code == 201
    return {
        "email": "alice@example.com",
        "token": reg.json()["access_token"],
        "user_id": reg.json()["user"]["id"],
        "headers": {"Authorization": f"Bearer {reg.json()['access_token']}"},
    }


@pytest.fixture
def auth_user_b(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "password456"},
    )
    assert reg.status_code == 201
    return {
        "email": "bob@example.com",
        "token": reg.json()["access_token"],
        "user_id": reg.json()["user"]["id"],
        "headers": {"Authorization": f"Bearer {reg.json()['access_token']}"},
    }
