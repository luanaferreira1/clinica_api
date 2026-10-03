import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.config import get_settings
from app.database import get_engine, seed_usuarios
from app.main import app


@pytest.fixture(autouse=True)
def preparar_banco_relacional(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("DATABASE_ECHO", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "segredo-exclusivo-dos-testes-com-mais-de-32-caracteres")
    monkeypatch.setenv("ADMIN_MFA_CODE", "654321")
    get_settings.cache_clear()
    get_engine.cache_clear()
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_usuarios(session)
    yield
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def db_session() -> Session:
    with Session(get_engine()) as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_profissional(client: TestClient) -> dict[str, str]:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "profissional7",
            "password": "Profissional@123",
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def auth_recepcionista(client: TestClient) -> dict[str, str]:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "recepcao",
            "password": "Recepcao@123",
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def auth_admin(client: TestClient) -> dict[str, str]:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "admin",
            "password": "Admin@123",
            "mfa_code": "654321",
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def auth_paciente1(client: TestClient) -> dict[str, str]:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "paciente1",
            "password": "Paciente@123",
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}
