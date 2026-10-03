from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ConsultaDB(SQLModel, table=True):

    __tablename__ = "consultas"

    id: int | None = Field(default=None, primary_key=True)
    paciente_id: int = Field(index=True, gt=0)
    profissional_id: int = Field(index=True, gt=0)
    data_hora: datetime = Field(index=True)
    motivo: str = Field(max_length=500)
    observacoes: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="agendada", max_length=20, index=True)
    criado_em: datetime = Field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime = Field(default_factory=lambda: datetime.now(UTC))
    auditoria_id: UUID = Field(default_factory=uuid4, unique=True, index=True)


class UsuarioDB(SQLModel, table=True):

    __tablename__ = "usuarios"

    username: str = Field(primary_key=True, max_length=50)
    nome: str = Field(max_length=120)
    papel: str = Field(max_length=20, index=True)
    paciente_id: int | None = Field(default=None, index=True)
    profissional_id: int | None = Field(default=None, index=True)
    ativo: bool = Field(default=True, index=True)
    mfa_habilitado: bool = False
    senha_hash: str = Field(max_length=60)
