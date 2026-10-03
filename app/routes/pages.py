from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.auth import exigir_acesso_agenda
from app.database import consulta_repository, get_session
from app.models import UsuarioInternal
from app.templates import templates


router = APIRouter(tags=["páginas internas"])


@router.get("/agenda", response_class=HTMLResponse)
def exibir_agenda(
    request: Request,
    usuario: Annotated[UsuarioInternal, Depends(exigir_acesso_agenda)],
    session: Annotated[Session, Depends(get_session)],
    data: date | None = None,
) -> HTMLResponse:
    data_selecionada = data or date.today()
    consultas = [
        consulta.para_resposta()
        for consulta in consulta_repository.listar(session)
        if consulta.data_hora.date() == data_selecionada
    ]
    consultas.sort(key=lambda consulta: consulta.data_hora)

    return templates.TemplateResponse(
        request=request,
        name="agenda.html",
        context={
            "data_selecionada": data_selecionada,
            "consultas": consultas,
        },
    )

