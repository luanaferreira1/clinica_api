from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.auth import (
    autorizar_criacao_consulta,
    filtrar_consultas_visiveis,
    obter_consulta_para_gerenciamento,
    obter_consulta_para_leitura,
    obter_usuario_atual,
)
from app.database import consulta_repository, get_session
from app.models import (
    ConsultaCreate,
    ConsultaFiltros,
    ConsultaInternal,
    ConsultaPublic,
    ConsultaUpdate,
    UsuarioInternal,
)


router = APIRouter(prefix="/consultas", tags=["consultas"])


@router.post("", response_model=ConsultaPublic, status_code=status.HTTP_201_CREATED)
def criar_consulta(
    dados: ConsultaCreate,
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
    session: Annotated[Session, Depends(get_session)],
) -> ConsultaInternal:
    autorizar_criacao_consulta(usuario, dados.profissional_id)
    return consulta_repository.criar(session, dados)


@router.get("", response_model=list[ConsultaPublic])
def listar_consultas(
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
    filtros: Annotated[ConsultaFiltros, Query()],
    session: Annotated[Session, Depends(get_session)],
) -> list[ConsultaInternal]:
    consultas = consulta_repository.listar(
        session,
        status=filtros.status,
        busca=filtros.busca,
    )
    consultas = filtrar_consultas_visiveis(usuario, consultas)
    return consultas


@router.get("/{consulta_id}", response_model=ConsultaPublic)
def obter_consulta(
    consulta: Annotated[ConsultaInternal, Depends(obter_consulta_para_leitura)],
) -> ConsultaInternal:
    return consulta


@router.patch("/{consulta_id}", response_model=ConsultaPublic)
def atualizar_consulta(
    dados: ConsultaUpdate,
    consulta_existente: Annotated[
        ConsultaInternal,
        Depends(obter_consulta_para_gerenciamento),
    ],
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
    session: Annotated[Session, Depends(get_session)],
) -> ConsultaInternal:
    if dados.profissional_id is not None:
        autorizar_criacao_consulta(usuario, dados.profissional_id)
    consulta = consulta_repository.atualizar(session, consulta_existente.id, dados)
    if consulta is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consulta foi removida")
    return consulta


@router.delete("/{consulta_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_consulta(
    consulta: Annotated[
        ConsultaInternal,
        Depends(obter_consulta_para_gerenciamento),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    if not consulta_repository.excluir(session, consulta.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consulta foi removida")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

