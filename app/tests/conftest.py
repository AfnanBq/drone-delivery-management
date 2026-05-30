import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models.drones import Drones
from app.models.orders import Orders
from app.models.users import Users


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clear_database(db: Session):
    db.execute(delete(Orders))
    db.execute(delete(Drones))
    db.execute(delete(Users))
    db.commit()
    yield
    db.rollback()
    db.execute(delete(Orders))
    db.execute(delete(Drones))
    db.execute(delete(Users))
    db.commit()
