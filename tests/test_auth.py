from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import criar_token_acesso, verificar_senha
from app.config import JWT_ALGORITHM, JWT_HUMAN_AUDIENCE, JWT_ISSUER
from app.database import consulta_repository, usuario_repository
from app.models import ConsultaCreate


def test_senha_armazenada_com_bcrypt(db_session: Session) -> None:
    usuario = usuario_repository.obter(db_session, "profissional7")

    assert usuario is not None
    assert usuario.senha_hash.startswith("$2b$12$")
    assert usuario.senha_hash != "Profissional@123"
    assert verificar_senha("Profissional@123", usuario.senha_hash)


def test_login_emite_jwt_com_expiracao_e_claims(client: TestClient) -> None:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "profissional7",
            "password": "Profissional@123",
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    payload = jwt.decode(
        corpo["access_token"],
        "segredo-exclusivo-dos-testes-com-mais-de-32-caracteres",
        algorithms=[JWT_ALGORITHM],
        audience=JWT_HUMAN_AUDIENCE,
        issuer=JWT_ISSUER,
    )
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == 1800
    assert payload["sub"] == "profissional7"
    assert payload["role"] == "profissional"
    assert payload["professional_id"] == 7
    assert payload["exp"] > payload["iat"]


def test_rota_protegida_rejeita_requisicao_sem_token(client: TestClient) -> None:
    resposta = client.get("/consultas")

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Not authenticated"}


def test_login_rejeita_senha_incorreta(client: TestClient) -> None:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "profissional7",
            "password": "senha-incorreta",
        },
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Usuário ou senha inválidos"}


def test_admin_precisa_informar_mfa(client: TestClient) -> None:
    resposta = client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": "admin",
            "password": "Admin@123",
        },
    )

    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Código MFA obrigatório para administradores"}


def test_admin_com_mfa_acessa_rota_restrita(
    client: TestClient,
    auth_admin: dict[str, str],
) -> None:
    resposta = client.get("/admin/usuarios", headers=auth_admin)

    assert resposta.status_code == 200
    assert len(resposta.json()) == 6
    assert all("senha_hash" not in usuario for usuario in resposta.json())


def test_usuario_sem_papel_admin_e_impedido_de_acessar_rota_restrita(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.get("/admin/usuarios", headers=auth_profissional)

    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Acesso restrito a administradores"}


def test_profissional_nao_acessa_consulta_de_outro_profissional(
    client: TestClient,
    auth_profissional: dict[str, str],
    db_session: Session,
) -> None:
    consulta = consulta_repository.criar(
        db_session,
        ConsultaCreate(
            paciente_id=2,
            profissional_id=8,
            data_hora="2030-05-21T10:00:00-03:00",
            motivo="Retorno com outro profissional",
        )
    )

    resposta = client.get(f"/consultas/{consulta.id}", headers=auth_profissional)

    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Usuário sem permissão sobre esta consulta"}


def test_profissional_nao_cria_consulta_para_outro_profissional(
    client: TestClient,
    auth_profissional: dict[str, str],
) -> None:
    resposta = client.post(
        "/consultas",
        json={
            "paciente_id": 2,
            "profissional_id": 8,
            "data_hora": "2030-05-21T10:00:00-03:00",
            "motivo": "Tentativa de quebra de ownership",
        },
        headers=auth_profissional,
    )

    assert resposta.status_code == 403
    assert resposta.json() == {"detail": "Usuário sem permissão sobre esta consulta"}


def test_token_expirado_e_rejeitado(client: TestClient, db_session: Session) -> None:
    usuario = usuario_repository.obter(db_session, "profissional7")
    assert usuario is not None
    token, _ = criar_token_acesso(usuario, True, timedelta(seconds=-1))

    resposta = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Credenciais de autenticação inválidas"}
