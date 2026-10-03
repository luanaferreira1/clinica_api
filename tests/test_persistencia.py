from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import Settings
from app.database import consulta_repository, get_engine
from app.models import ConsultaCreate


CONSULTA_PERSISTENTE = ConsultaCreate(
    paciente_id=1,
    profissional_id=7,
    data_hora="2030-08-10T09:30:00-03:00",
    motivo="Consulta persistida no banco relacional",
    observacoes="Registro usado no teste de reinicialização.",
)


def test_consulta_permanece_apos_nova_conexao(tmp_path: Path) -> None:
    arquivo_banco = tmp_path / "persistencia.db"
    url = f"sqlite:///{arquivo_banco.as_posix()}"
    engine_inicial = create_engine(url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine_inicial)

    with Session(engine_inicial) as session:
        criada = consulta_repository.criar(session, CONSULTA_PERSISTENTE)
        consulta_id = criada.id

    engine_inicial.dispose()
    engine_reiniciado = create_engine(url, connect_args={"check_same_thread": False})

    with Session(engine_reiniciado) as session:
        recuperada = consulta_repository.obter(session, consulta_id)

    engine_reiniciado.dispose()
    assert recuperada is not None
    assert recuperada.motivo == "Consulta persistida no banco relacional"


def test_filtro_sql_usa_parametro_vinculado() -> None:
    engine = get_engine()
    execucoes: list[tuple[str, object]] = []

    def capturar_query(
        _conexao,
        _cursor,
        statement,
        parametros,
        _contexto,
        _executemany,
    ) -> None:
        execucoes.append((statement, parametros))

    event.listen(engine, "before_cursor_execute", capturar_query)
    try:
        with Session(engine) as session:
            consulta_repository.listar(session, status="agendada")
    finally:
        event.remove(engine, "before_cursor_execute", capturar_query)

    assert any(
        "consultas.status = ?" in statement and parametros == ("agendada",)
        for statement, parametros in execucoes
    )


def test_basesettings_carrega_configuracao_de_arquivo_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for nome in (
        "APP_NAME",
        "APP_ENV",
        "DATABASE_URL",
        "DATABASE_ECHO",
        "JWT_SECRET_KEY",
        "ADMIN_MFA_CODE",
    ):
        monkeypatch.delenv(nome, raising=False)

    arquivo_env = tmp_path / ".env"
    arquivo_env.write_text(
        "APP_NAME=Clínica Teste\n"
        "APP_ENV=test\n"
        "DATABASE_URL=sqlite:///./teste-config.db\n"
        "DATABASE_ECHO=false\n"
        "JWT_SECRET_KEY=segredo-de-teste-com-mais-de-32-caracteres\n"
        "ADMIN_MFA_CODE=123456\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=arquivo_env)

    assert settings.database_url == "sqlite:///./teste-config.db"
    assert settings.admin_mfa_code == "123456"
    assert str(settings.jwt_secret_key) == "**********"
