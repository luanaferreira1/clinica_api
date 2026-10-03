from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import inicializar_banco
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.consultas import router as consultas_router
from app.routes.pages import router as pages_router
from app.routes.prontuarios import router as prontuarios_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    inicializar_banco()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="API de Agendamento de Consultas",
        description="API REST modular para gerenciamento de consultas médicas.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(auth_router)
    application.include_router(consultas_router)
    application.include_router(pages_router)
    application.include_router(admin_router)
    application.include_router(prontuarios_router)

    @application.get("/health", tags=["infraestrutura"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()

