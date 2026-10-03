from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import consulta_repository


CONSULTA_VALIDA = {
    "paciente_id": 1,
    "profissional_id": 7,
    "data_hora": "2030-05-20T14:30:00-03:00",
    "motivo": "Consulta de acompanhamento",
    "observacoes": "Paciente deve levar os exames anteriores.",
}

CAMPOS_PUBLICOS = {
    "id",
    "paciente_id",
    "profissional_id",
    "data_hora",
    "motivo",
    "observacoes",
    "status",
}


def test_criar_consulta_com_sucesso(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.post("/consultas", json=CONSULTA_VALIDA, headers=auth_profissional)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["paciente_id"] == 1
    assert corpo["profissional_id"] == 7
    assert corpo["status"] == "agendada"
    assert set(corpo) == CAMPOS_PUBLICOS


def test_fluxo_crud_completo(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    criada = client.post("/consultas", json=CONSULTA_VALIDA, headers=auth_profissional)
    consulta_id = criada.json()["id"]

    listagem = client.get("/consultas", headers=auth_profissional)
    assert listagem.status_code == 200
    assert len(listagem.json()) == 1

    consulta = client.get(f"/consultas/{consulta_id}", headers=auth_profissional)
    assert consulta.status_code == 200
    assert consulta.json()["motivo"] == "Consulta de acompanhamento"

    atualizada = client.patch(
        f"/consultas/{consulta_id}",
        json={"status": "confirmada"},
        headers=auth_profissional,
    )
    assert atualizada.status_code == 200
    assert atualizada.json()["status"] == "confirmada"

    excluida = client.delete(f"/consultas/{consulta_id}", headers=auth_profissional)
    assert excluida.status_code == 204
    assert client.get(f"/consultas/{consulta_id}", headers=auth_profissional).status_code == 404


def test_consulta_inexistente_retorna_404(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.get("/consultas/999", headers=auth_profissional)

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Consulta não encontrada"}


def test_response_model_oculta_campos_internos(
    client: TestClient,
    auth_profissional: dict[str, str],
    db_session: Session,
) -> None:
    resposta = client.post("/consultas", json=CONSULTA_VALIDA, headers=auth_profissional)
    registro_interno = consulta_repository.obter(db_session, 1)

    assert resposta.status_code == 201
    assert registro_interno is not None
    assert registro_interno.auditoria_id is not None
    assert set(resposta.json()) == CAMPOS_PUBLICOS
    assert "auditoria_id" not in resposta.json()
    assert "criado_em" not in resposta.json()
    assert "atualizado_em" not in resposta.json()


def test_agenda_html_aplica_autoescape_contra_xss(
    client: TestClient,
    auth_profissional: dict[str, str],
    auth_recepcionista: dict[str, str],
) -> None:
    payload_malicioso = {
        **CONSULTA_VALIDA,
        "observacoes": '<script>alert("XSS")</script>',
    }
    criada = client.post("/consultas", json=payload_malicioso, headers=auth_profissional)

    resposta = client.get("/agenda?data=2030-05-20", headers=auth_recepcionista)

    assert criada.status_code == 201
    assert resposta.status_code == 200
    assert "Área interna da recepção" in resposta.text
    assert "<script>" not in resposta.text
    assert "&lt;script&gt;" in resposta.text
    assert "auditoria_id" not in resposta.text

