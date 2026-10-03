from datetime import UTC, datetime

from sqlalchemy import or_
from sqlmodel import Session, select

from app.database.tables import ConsultaDB
from app.models import ConsultaCreate, ConsultaInternal, ConsultaUpdate


def para_consulta_internal(registro: ConsultaDB) -> ConsultaInternal:
    return ConsultaInternal.model_validate(registro.model_dump())


class ConsultaRepository:

    def listar(
        self,
        session: Session,
        status: str | None = None,
        busca: str | None = None,
    ) -> list[ConsultaInternal]:
        statement = select(ConsultaDB)
        if status is not None:
            statement = statement.where(ConsultaDB.status == status)
        if busca is not None:
            statement = statement.where(
                or_(
                    ConsultaDB.motivo.contains(busca),
                    ConsultaDB.observacoes.contains(busca),
                )
            )
        statement = statement.order_by(ConsultaDB.data_hora, ConsultaDB.id)
        return [para_consulta_internal(registro) for registro in session.exec(statement).all()]

    def obter(self, session: Session, consulta_id: int) -> ConsultaInternal | None:
        registro = session.get(ConsultaDB, consulta_id)
        return para_consulta_internal(registro) if registro is not None else None

    def criar(self, session: Session, dados: ConsultaCreate) -> ConsultaInternal:
        registro = ConsultaDB.model_validate(dados)
        session.add(registro)
        session.commit()
        session.refresh(registro)
        return para_consulta_internal(registro)

    def atualizar(
        self,
        session: Session,
        consulta_id: int,
        dados: ConsultaUpdate,
    ) -> ConsultaInternal | None:
        registro = session.get(ConsultaDB, consulta_id)
        if registro is None:
            return None
        registro.sqlmodel_update(
            {
                **dados.model_dump(exclude_unset=True),
                "atualizado_em": datetime.now(UTC),
            }
        )
        session.add(registro)
        session.commit()
        session.refresh(registro)
        return para_consulta_internal(registro)

    def excluir(self, session: Session, consulta_id: int) -> bool:
        registro = session.get(ConsultaDB, consulta_id)
        if registro is None:
            return False
        session.delete(registro)
        session.commit()
        return True


consulta_repository = ConsultaRepository()
