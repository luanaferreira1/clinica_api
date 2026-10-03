from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import obter_consulta_para_leitura, obter_usuario_atual
from app.models import ConsultaInternal, ConsultaPublic, UsuarioInternal


router = APIRouter(prefix="/pacientes/consultas", tags=["prontuários"])


@router.get("/{consulta_id}", response_model=ConsultaPublic)
def obter_prontuario_consulta(
    consulta: Annotated[ConsultaInternal, Depends(obter_consulta_para_leitura)],
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
) -> ConsultaInternal:
    if usuario.papel != "paciente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a pacientes",
        )
    return consulta
