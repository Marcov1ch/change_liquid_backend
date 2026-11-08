from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.common.enums import ComponentType
from app.db.models import RepairComponentDB, RepairDB, ReplacementDB
from app.services.dto import RepairDTO


class RepairRepository:
    """Репозиторий для работы с ремонтами."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_repair: RepairDB) -> RepairDTO:
        """Преобразовать ORM-модель в DTO."""
        return RepairDTO(
            id=db_repair.id,
            vehicle_id=db_repair.vehicle_id,
            repair_date=db_repair.repair_date,
            km_at_repair=db_repair.km_at_repair,
            description=db_repair.description,
            work_cost=db_repair.work_cost,
            parts_cost=db_repair.parts_cost,
            component_types=[
                ComponentType(component.component_type)
                for component in sorted(db_repair.components, key=lambda c: c.id or 0)
            ],
        )

    def save(self, repair: RepairDTO, commit: bool = True) -> RepairDTO:
        """Создать или обновить ремонт и его компоненты."""
        if repair.id:
            db_repair = self.db.query(RepairDB).filter(
                RepairDB.id == repair.id
            ).first()
            if not db_repair:
                raise ValueError(f'Repair with id {repair.id} not found')

            db_repair.vehicle_id = repair.vehicle_id
            db_repair.repair_date = repair.repair_date
            db_repair.km_at_repair = repair.km_at_repair
            db_repair.description = repair.description
            db_repair.work_cost = repair.work_cost
            db_repair.parts_cost = repair.parts_cost

            db_repair.components.clear()
            self.db.flush()
            for component_type in repair.component_types:
                db_repair.components.append(
                    RepairComponentDB(component_type=component_type.value)
                )
        else:
            db_repair = RepairDB(
                vehicle_id=repair.vehicle_id,
                repair_date=repair.repair_date,
                km_at_repair=repair.km_at_repair,
                description=repair.description,
                work_cost=repair.work_cost,
                parts_cost=repair.parts_cost,
            )
            for component_type in repair.component_types:
                db_repair.components.append(
                    RepairComponentDB(component_type=component_type.value)
                )
            self.db.add(db_repair)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_repair)

        return self._to_dto(db_repair)

    def find_by_id(self, repair_id: int) -> RepairDTO | None:
        """Найти ремонт по id."""
        db_repair = self.db.query(RepairDB).options(
            selectinload(RepairDB.components)
        ).filter(RepairDB.id == repair_id).first()
        return self._to_dto(db_repair) if db_repair else None

    def find_by_vehicle_id(self, vehicle_id: int) -> list[RepairDTO]:
        """Найти ремонты автомобиля (сначала новые)."""
        db_repairs = self.db.query(RepairDB).options(
            selectinload(RepairDB.components)
        ).filter(
            RepairDB.vehicle_id == vehicle_id
        ).order_by(
            RepairDB.repair_date.desc(),
            RepairDB.id.desc(),
        ).all()
        return [self._to_dto(repair) for repair in db_repairs]

    def find_repair_for_replacement(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        repair_date: date,
    ) -> RepairDTO | None:
        """Найти ремонт, в который входит компонент на указанную дату."""
        db_repair = self.db.query(RepairDB).options(
            selectinload(RepairDB.components)
        ).join(
            RepairComponentDB,
            RepairComponentDB.repair_id == RepairDB.id,
        ).filter(
            RepairDB.vehicle_id == vehicle_id,
            RepairDB.repair_date == repair_date,
            RepairComponentDB.component_type == component_type.value,
        ).first()
        return self._to_dto(db_repair) if db_repair else None

    def find_priced_component_types(
        self,
        vehicle_id: int,
        repair_date: date,
        component_types: list[ComponentType],
        exclude_replacement_ids: set[int] | None = None,
    ) -> set[str]:
        """Найти компоненты ремонта, для которых уже есть платная замена."""
        if not component_types:
            return set()

        query = self.db.query(ReplacementDB.component_type).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.replacement_date == repair_date,
            ReplacementDB.component_type.in_(
                [component_type.value for component_type in component_types]
            ),
            or_(
                ReplacementDB.component_price > 0,
                ReplacementDB.work_price > 0,
            ),
        )
        if exclude_replacement_ids:
            query = query.filter(ReplacementDB.id.notin_(exclude_replacement_ids))

        return {row[0] for row in query.all()}

    def delete(self, repair_id: int, commit: bool = True) -> bool:
        """Удалить ремонт и его компоненты."""
        db_repair = self.db.query(RepairDB).options(
            selectinload(RepairDB.components)
        ).filter(RepairDB.id == repair_id).first()
        if not db_repair:
            return False

        self.db.delete(db_repair)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return True

    def delete_by_vehicle_id(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все ремонты автомобиля. Возвращает количество удалённых."""
        repair_ids = [
            row[0] for row in self.db.query(RepairDB.id).filter(
                RepairDB.vehicle_id == vehicle_id
            ).all()
        ]
        if not repair_ids:
            return 0

        self.db.query(RepairComponentDB).filter(
            RepairComponentDB.repair_id.in_(repair_ids)
        ).delete(synchronize_session=False)
        count = self.db.query(RepairDB).filter(
            RepairDB.id.in_(repair_ids)
        ).delete(synchronize_session=False)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return count  # type: ignore[no-any-return]
