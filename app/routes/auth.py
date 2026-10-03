from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestFormStrict
from sqlmodel import Session

from app.auth import autenticar_usuario, criar_token_acesso, obter_usuario_atual
from app.config import get_admin_mfa_code
from app.database import get_session
from app.models import TokenResponse, UsuarioInternal, UsuarioPublic


router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/token", response_model=TokenResponse)
def emitir_token(
    formulario: Annotated[OAuth2PasswordRequestFormStrict, Depends()],
    session: Annotated[Session, Depends(get_session)],
    mfa_code: Annotated[str | None, Form(min_length=6, max_length=6)] = None,
) -> TokenResponse:
    usuario = autenticar_usuario(session, formulario.username, formulario.password)
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    mfa_verificado = not usuario.mfa_habilitado
    if usuario.mfa_habilitado:
        if mfa_code is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Código MFA obrigatório para administradores",
            )
        try:
            codigo_esperado = get_admin_mfa_code()
        except RuntimeError as erro:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MFA administrativo indisponível",
            ) from erro
        if not compare_digest(mfa_code, codigo_esperado):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código MFA inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        mfa_verificado = True

    token, expires_in = criar_token_acesso(usuario, mfa_verificado)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UsuarioPublic)
def obter_perfil(
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
) -> UsuarioInternal:
    return usuario
