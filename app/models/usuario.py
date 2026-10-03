from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.models.base import ModeloEstrito


PapelUsuario = Literal["paciente", "recepcionista", "profissional", "administrador"]
NomeUsuario = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[a-z0-9._-]+$"),
]


class UsuarioPublic(ModeloEstrito):

    username: NomeUsuario
    nome: str = Field(min_length=3, max_length=120)
    papel: PapelUsuario
    paciente_id: int | None = Field(default=None, gt=0)
    profissional_id: int | None = Field(default=None, gt=0)
    ativo: bool = True
    mfa_habilitado: bool = False


class UsuarioInternal(UsuarioPublic):

    senha_hash: str = Field(min_length=60, max_length=60, repr=False)


class TokenResponse(ModeloEstrito):

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)


class TokenPayload(ModeloEstrito):

    sub: NomeUsuario
    role: PapelUsuario
    patient_id: int | None = Field(default=None, gt=0)
    professional_id: int | None = Field(default=None, gt=0)
    mfa: bool
    token_type: Literal["access"]
    iss: Literal["clinicas-api"]
    aud: Literal["clinicas-clientes-humanos"]
    iat: int
    exp: int
    jti: str = Field(min_length=36, max_length=36)
