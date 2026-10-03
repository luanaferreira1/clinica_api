from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import consulta_repository
from app.models import ConsultaCreate


def criar_consulta(
    session: Session,
    paciente_id: int,
    profissional_id: int,
) -> None:
    consulta_repository.criar(
        session,
        ConsultaCreate(
            paciente_id=paciente_id,
            profissional_id=profissional_id,
            data_hora="2030-06-12T09:00:00-03:00",
            motivo="Consulta de acompanhamento",
            observacoes="Retorno programado.",
        )
    )


def test_endpoint_adicional_lista_somente_consultas_do_paciente(
    client: TestClient,
    auth_paciente1: dict[str, str],
    db_session: Session,
) -> None:
    criar_consulta(db_session, 1, 7)
    criar_consulta(db_session, 2, 8)

    resposta = client.get("/consultas", headers=auth_paciente1)

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["paciente_id"] == 1


def test_status_aplica_whitelist_e_rejeita_sql_injection(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.get(
        "/consultas",
        params={"status": "agendada' OR 1=1--"},
        headers=auth_profissional,
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["type"] == "literal_error"


def test_busca_aplica_regex_e_rejeita_sql_injection(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.get(
        "/consultas",
        params={"busca": "'; DROP TABLE consultas;--"},
        headers=auth_profissional,
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["type"] == "string_pattern_mismatch"


def test_modelo_rejeita_campo_nao_declarado(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.post(
        "/consultas",
        json={
            "paciente_id": 1,
            "profissional_id": 7,
            "data_hora": "2030-06-12T09:00:00-03:00",
            "motivo": "Consulta de acompanhamento",
            "observacoes": "Retorno programado.",
            "papel": "administrador",
        },
        headers=auth_profissional,
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["type"] == "extra_forbidden"
