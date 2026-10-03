import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import JWT_ALGORITHM, JWT_HUMAN_AUDIENCE, JWT_ISSUER
from app.database import consulta_repository
from app.models import ConsultaCreate


CHAVE_TESTES = "segredo-exclusivo-dos-testes-com-mais-de-32-caracteres"


def criar_consulta_alheia(session: Session):
    return consulta_repository.criar(
        session,
        ConsultaCreate(
            paciente_id=2,
            profissional_id=8,
            data_hora="2030-09-18T10:00:00-03:00",
            motivo="Consulta protegida pelo threat model",
        ),
    )


def test_tm01_token_com_papel_adulterado_e_rejeitado(client: TestClient) -> None:
    login = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "profissional7",
            "password": "Profissional@123",
        },
    )
    payload = jwt.decode(
        login.json()["access_token"],
        CHAVE_TESTES,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_HUMAN_AUDIENCE,
        issuer=JWT_ISSUER,
    )
    payload["role"] = "administrador"
    token_adulterado = jwt.encode(payload, CHAVE_TESTES, algorithm=JWT_ALGORITHM)

    resposta = client.get(
        "/admin/usuarios",
        headers={"Authorization": f"Bearer {token_adulterado}"},
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Credenciais de autenticação inválidas"}


def test_tm03_recepcionista_nao_altera_consulta(
    client: TestClient,
    auth_recepcionista: dict[str, str],
    db_session: Session,
) -> None:
    consulta = criar_consulta_alheia(db_session)

    resposta = client.patch(
        f"/consultas/{consulta.id}",
        json={"status": "cancelada"},
        headers=auth_recepcionista,
    )
    preservada = consulta_repository.obter(db_session, consulta.id)

    assert resposta.status_code == 403
    assert preservada is not None
    assert preservada.status == "agendada"


def test_tm03_recepcionista_nao_exclui_consulta(
    client: TestClient,
    auth_recepcionista: dict[str, str],
    db_session: Session,
) -> None:
    consulta = criar_consulta_alheia(db_session)

    resposta = client.delete(
        f"/consultas/{consulta.id}",
        headers=auth_recepcionista,
    )
    preservada = consulta_repository.obter(db_session, consulta.id)

    assert resposta.status_code == 403
    assert preservada is not None


def test_tm08_profissional_nao_acessa_agenda_interna(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.get(
        "/agenda?data=2030-09-18",
        headers=auth_profissional,
    )

    assert resposta.status_code == 403
    assert resposta.json() == {
        "detail": "Agenda restrita à recepção e aos administradores"
    }


def test_tm08_recepcionista_acessa_agenda_interna(
    client: TestClient,
    auth_recepcionista: dict[str, str],
) -> None:
    resposta = client.get(
        "/agenda?data=2030-09-18",
        headers=auth_recepcionista,
    )

    assert resposta.status_code == 200
    assert "Área interna da recepção" in resposta.text
