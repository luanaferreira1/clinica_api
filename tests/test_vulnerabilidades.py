from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import consulta_repository
from app.models import ConsultaCreate


def test_bola_paciente_nao_acessa_consulta_de_outro_paciente(
    client: TestClient,
    auth_paciente1: dict[str, str],
    db_session: Session,
) -> None:
    consulta_paciente2 = consulta_repository.criar(
        db_session,
        ConsultaCreate(
            paciente_id=2,
            profissional_id=8,
            data_hora="2030-06-12T09:00:00-03:00",
            motivo="Acompanhamento cardiológico",
            observacoes="Paciente relata histórico familiar de hipertensão.",
        )
    )

    resposta = client.get(
        f"/pacientes/consultas/{consulta_paciente2.id}",
        headers=auth_paciente1,
    )

    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Usuário sem permissão sobre esta consulta"}


def test_login_nao_aplica_rate_limit_apos_tentativas_invalidas(client: TestClient) -> None:
    respostas = [
        client.post(
            "/auth/token",
            data={
                "grant_type": "password",
                "username": "profissional7",
                "password": f"senha-invalida-{tentativa}",
            },
        )
        for tentativa in range(1, 7)
    ]

    assert [resposta.status_code for resposta in respostas] == [401] * 6
    assert all(resposta.status_code != 429 for resposta in respostas)


def test_headers_de_seguranca_ainda_nao_foram_configurados(client: TestClient) -> None:
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert "strict-transport-security" not in resposta.headers
    assert "x-frame-options" not in resposta.headers
    assert "x-content-type-options" not in resposta.headers
