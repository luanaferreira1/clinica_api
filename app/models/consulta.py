from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.models.base import ModeloEstrito


PadraoTextoClinico = r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9][A-Za-zÀ-ÖØ-öø-ÿ0-9 .,'()/-]*$"
TextoMotivo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=500,
        pattern=PadraoTextoClinico,
    ),
]
TextoObservacao = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
TextoBusca = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=80,
        pattern=PadraoTextoClinico,
    ),
]
StatusConsulta = Literal["agendada", "confirmada", "cancelada", "concluida"]


class ConsultaFiltros(ModeloEstrito):

    status: StatusConsulta | None = None
    busca: TextoBusca | None = None


class ConsultaCreate(ModeloEstrito):

    paciente_id: int = Field(gt=0)
    profissional_id: int = Field(gt=0)
    data_hora: datetime
    motivo: TextoMotivo
    observacoes: TextoObservacao | None = None
    status: StatusConsulta = "agendada"

    @field_validator("data_hora")
    @classmethod
    def validar_fuso_horario(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("data_hora deve incluir o fuso horário")
        return valor


class ConsultaUpdate(ModeloEstrito):

    paciente_id: int | None = Field(default=None, gt=0)
    profissional_id: int | None = Field(default=None, gt=0)
    data_hora: datetime | None = None
    motivo: TextoMotivo | None = None
    observacoes: TextoObservacao | None = None
    status: StatusConsulta | None = None

    @field_validator("data_hora")
    @classmethod
    def validar_fuso_horario(cls, valor: datetime | None) -> datetime | None:
        if valor is not None and (valor.tzinfo is None or valor.utcoffset() is None):
            raise ValueError("data_hora deve incluir o fuso horário")
        return valor

    @model_validator(mode="after")
    def validar_corpo_nao_vazio(self) -> "ConsultaUpdate":
        if not self.model_fields_set:
            raise ValueError("informe ao menos um campo para atualização")
        return self


class ConsultaPublic(ModeloEstrito):

    id: int
    paciente_id: int
    profissional_id: int
    data_hora: datetime
    motivo: str
    observacoes: str | None
    status: StatusConsulta


class ConsultaInternal(ConsultaPublic):

    criado_em: datetime
    atualizado_em: datetime
    auditoria_id: UUID

    def para_resposta(self) -> ConsultaPublic:
        campos_publicos = set(ConsultaPublic.model_fields)
        return ConsultaPublic.model_validate(self.model_dump(include=campos_publicos))

