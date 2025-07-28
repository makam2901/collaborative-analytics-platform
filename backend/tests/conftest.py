import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel
from main import app, get_session

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def override_get_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

@pytest.fixture(scope="module")
def client():
    SQLModel.metadata.create_all(engine)
    yield TestClient(app)
    SQLModel.metadata.drop_all(engine)