from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings
from app.database.tables import ConsultaDB, UsuarioDB


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    opcoes: dict[str, object] = {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("sqlite"):
        opcoes["connect_args"] = {"check_same_thread": False}
        if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
            opcoes["poolclass"] = StaticPool
    return create_engine(settings.database_url, **opcoes)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def criar_tabelas() -> None:
    SQLModel.metadata.create_all(get_engine())


def inicializar_banco() -> None:
    from app.database.users import seed_usuarios

    criar_tabelas()
    with Session(get_engine()) as session:
        seed_usuarios(session)
