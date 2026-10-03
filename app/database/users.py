from sqlmodel import Session, select

from app.database.tables import UsuarioDB
from app.models import UsuarioInternal


USUARIOS_INICIAIS = (
    UsuarioInternal(
        username="paciente1",
        nome="Paciente Um",
        papel="paciente",
        paciente_id=1,
        senha_hash="$2b$12$S3ROGtNm3bVO0bPXk4yeWO57TGP8c.kTyx86jIS7lVVEElE9XVAmO",
    ),
    UsuarioInternal(
        username="paciente2",
        nome="Paciente Dois",
        papel="paciente",
        paciente_id=2,
        senha_hash="$2b$12$S3ROGtNm3bVO0bPXk4yeWO57TGP8c.kTyx86jIS7lVVEElE9XVAmO",
    ),
    UsuarioInternal(
        username="profissional7",
        nome="Profissional Sete",
        papel="profissional",
        profissional_id=7,
        senha_hash="$2b$12$WdmDWhaCuso/UTkoINrsb.a7aSpBvrsf.iattdt3wagL0KdZoXo8C",
    ),
    UsuarioInternal(
        username="profissional8",
        nome="Profissional Oito",
        papel="profissional",
        profissional_id=8,
        senha_hash="$2b$12$WdmDWhaCuso/UTkoINrsb.a7aSpBvrsf.iattdt3wagL0KdZoXo8C",
    ),
    UsuarioInternal(
        username="recepcao",
        nome="Recepção da Clínica",
        papel="recepcionista",
        senha_hash="$2b$12$6BGhBibiPPqVeHS3/d5qDevmtfe5v5bupUgmy0CQLaxdlV9YdreNi",
    ),
    UsuarioInternal(
        username="admin",
        nome="Administrador do Sistema",
        papel="administrador",
        mfa_habilitado=True,
        senha_hash="$2b$12$NCiR/1ZqHk/6sS.ndByL7.WbyJj7YuLWhtwxHj/6Hs7PBecK3es8e",
    ),
)


def para_usuario_internal(registro: UsuarioDB) -> UsuarioInternal:
    return UsuarioInternal.model_validate(registro.model_dump())


class UsuarioRepository:

    def obter(self, session: Session, username: str) -> UsuarioInternal | None:
        statement = select(UsuarioDB).where(UsuarioDB.username == username)
        registro = session.exec(statement).first()
        return para_usuario_internal(registro) if registro is not None else None

    def listar(self, session: Session) -> list[UsuarioInternal]:
        statement = select(UsuarioDB).order_by(UsuarioDB.username)
        return [para_usuario_internal(registro) for registro in session.exec(statement).all()]


def seed_usuarios(session: Session) -> None:
    for usuario in USUARIOS_INICIAIS:
        if session.get(UsuarioDB, usuario.username) is None:
            session.add(UsuarioDB.model_validate(usuario))
    session.commit()


usuario_repository = UsuarioRepository()
