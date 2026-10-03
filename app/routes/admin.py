from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import exigir_administrador
from app.database import get_session, usuario_repository
from app.models import UsuarioInternal, UsuarioPublic


router = APIRouter(prefix="/admin", tags=["administração"])


@router.get("/usuarios", response_model=list[UsuarioPublic])
def listar_usuarios(
    _: Annotated[UsuarioInternal, Depends(exigir_administrador)],
    session: Annotated[Session, Depends(get_session)],
) -> list[UsuarioInternal]:
    return usuario_repository.listar(session)
