from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_HUMAN_AUDIENCE,
    JWT_ISSUER,
    get_jwt_secret_key,
)
from app.database import consulta_repository, get_session, usuario_repository
from app.models import ConsultaInternal, TokenPayload, UsuarioInternal


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
OperacaoConsulta = Literal["leitura", "gerenciamento"]


def verificar_senha(senha: str, senha_hash: str) -> bool:
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > 72:
        return False
    return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))


def gerar_hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > 72:
        raise ValueError("A senha deve possuir no máximo 72 bytes")
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def autenticar_usuario(
    session: Session,
    username: str,
    senha: str,
) -> UsuarioInternal | None:
    usuario = usuario_repository.obter(session, username)
    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def criar_token_acesso(
    usuario: UsuarioInternal,
    mfa_verificado: bool,
    duracao: timedelta | None = None,
) -> tuple[str, int]:
    validade = duracao or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    agora = datetime.now(UTC)
    expira_em = agora + validade
    payload = {
        "sub": usuario.username,
        "role": usuario.papel,
        "patient_id": usuario.paciente_id,
        "professional_id": usuario.profissional_id,
        "mfa": mfa_verificado,
        "token_type": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_HUMAN_AUDIENCE,
        "iat": agora,
        "exp": expira_em,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return token, max(1, int(validade.total_seconds()))


def credenciais_invalidas() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais de autenticação inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obter_usuario_atual(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> UsuarioInternal:
    try:
        dados = jwt.decode(
            token,
            get_jwt_secret_key(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_HUMAN_AUDIENCE,
            issuer=JWT_ISSUER,
            options={
                "require": [
                    "sub",
                    "role",
                    "mfa",
                    "token_type",
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "jti",
                ]
            },
        )
        payload = TokenPayload.model_validate(dados)
    except (InvalidTokenError, RuntimeError, ValidationError):
        raise credenciais_invalidas()

    usuario = usuario_repository.obter(session, payload.sub)
    if usuario is None or not usuario.ativo:
        raise credenciais_invalidas()
    if (
        usuario.papel != payload.role
        or usuario.paciente_id != payload.patient_id
        or usuario.profissional_id != payload.professional_id
    ):
        raise credenciais_invalidas()
    if usuario.mfa_habilitado and not payload.mfa:
        raise credenciais_invalidas()
    return usuario


def exigir_administrador(
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
) -> UsuarioInternal:
    if usuario.papel != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return usuario


def exigir_acesso_agenda(
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
) -> UsuarioInternal:
    if usuario.papel not in {"recepcionista", "administrador"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agenda restrita à recepção e aos administradores",
        )
    return usuario


def autorizar_consulta(
    usuario: UsuarioInternal,
    consulta: ConsultaInternal,
    operacao: OperacaoConsulta,
) -> None:
    if (
        operacao == "leitura"
        and usuario.papel == "paciente"
        and usuario.paciente_id == consulta.paciente_id
    ):
        return
    if (
        usuario.papel == "profissional"
        and usuario.profissional_id == consulta.profissional_id
    ):
        return
    if operacao == "leitura" and usuario.papel in {"recepcionista", "administrador"}:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Usuário sem permissão sobre esta consulta",
    )


def autorizar_criacao_consulta(
    usuario: UsuarioInternal,
    profissional_id: int,
) -> None:
    if usuario.papel == "profissional" and usuario.profissional_id == profissional_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Usuário sem permissão sobre esta consulta",
    )


def obter_consulta_para_leitura(
    consulta_id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
    session: Annotated[Session, Depends(get_session)],
) -> ConsultaInternal:
    consulta = consulta_repository.obter(session, consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    autorizar_consulta(usuario, consulta, "leitura")
    return consulta


def obter_consulta_para_gerenciamento(
    consulta_id: Annotated[int, Path(gt=0)],
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
    session: Annotated[Session, Depends(get_session)],
) -> ConsultaInternal:
    consulta = consulta_repository.obter(session, consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    autorizar_consulta(usuario, consulta, "gerenciamento")
    return consulta


def filtrar_consultas_visiveis(
    usuario: UsuarioInternal,
    consultas: list[ConsultaInternal],
) -> list[ConsultaInternal]:
    if usuario.papel == "profissional":
        return [
            consulta
            for consulta in consultas
            if consulta.profissional_id == usuario.profissional_id
        ]
    if usuario.papel == "paciente":
        return [
            consulta
            for consulta in consultas
            if consulta.paciente_id == usuario.paciente_id
        ]
    if usuario.papel in {"recepcionista", "administrador"}:
        return consultas
    return []
