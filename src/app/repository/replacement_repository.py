from dataclasses import asdict
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import ReplacementDB
from app.common.enums import ComponentType
from app.services.dto import ReplacementDTO


class ReplacementRepository:
    """Репозиторий для работы с заменами в БД."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_row: ReplacementDB) -> ReplacementDTO:
        """Конвертировать ORM-модель в DTO."""
        return ReplacementDTO(
            id=db_row.id,
            vehicle_id=db_row.vehicle_id,
            component_type=ComponentType(db_row.component_type),
            component_name=db_row.component_name,
            component_price=db_row.component_price,
            work_price=db_row.work_price,
            replacement_date=db_row.replacement_date,
            km_at_replacement=db_row.km_at_replacement,
            interval_km=db_row.interval_km,
            next_change_date=db_row.next_change_date,
            interval_months=db_row.interval_months,
        )

    @staticmethod
    def _to_orm_data(replacement: ReplacementDTO) -> dict:
        """Преобразовать DTO в dict для ORM (component_type в строку)."""
        data = asdict(replacement)
        data.pop('id', None)
        if data.get('component_type'):
            data['component_type'] = data['component_type'].value
        return data

    def save(self, replacement: ReplacementDTO, commit: bool = True) -> ReplacementDTO:
        """Создать или обновить запись о замене."""
        if replacement.id:
            db_replacement = self.db.query(ReplacementDB).filter(
                ReplacementDB.id == replacement.id
            ).first()
            if not db_replacement:
                raise ValueError(f'Replacement with id {replacement.id} not found')

            for key, value in self._to_orm_data(replacement).items():
                setattr(db_replacement, key, value)
        else:
            db_replacement = ReplacementDB(**self._to_orm_data(replacement))
            self.db.add(db_replacement)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_replacement)

        return self._to_dto(db_replacement)

    def find_by_id(self, replacement_id: int) -> Optional[ReplacementDTO]:
        """Найти замену по id."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if not db_replacement:
            return None

        return self._to_dto(db_replacement)

    def find_by_vehicle_ids(self, vehicle_ids: list[int]) -> List[ReplacementDTO]:
        """Найти все замены для списка автомобилей."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id.in_(vehicle_ids)
        ).all()

        return [self._to_dto(replacement) for replacement in db_replacements]

    def find_by_vehicle_id(
        self,
        vehicle_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> List[ReplacementDTO]:
        """Найти замены для автомобиля (с опциональной пагинацией)."""
        query = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id
        ).order_by(ReplacementDB.id.asc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        db_replacements = query.all()
        return [self._to_dto(replacement) for replacement in db_replacements]

    def get_latest_replacement_ids(self, vehicle_id: int) -> set[int]:
        """Вернуть id последней замены по каждому типу компонента (max км, при равных — max id)."""
        from sqlalchemy import func, and_

        subq = (
            self.db.query(
                ReplacementDB.component_type,
                func.max(ReplacementDB.km_at_replacement).label('max_km'),
            )
            .filter(ReplacementDB.vehicle_id == vehicle_id)
            .group_by(ReplacementDB.component_type)
            .subquery()
        )

        rows = (
            self.db.query(ReplacementDB)
            .join(
                subq,
                and_(
                    ReplacementDB.component_type == subq.c.component_type,
                    ReplacementDB.km_at_replacement == subq.c.max_km,
                ),
            )
            .filter(ReplacementDB.vehicle_id == vehicle_id)
            .all()
        )

        best_by_type: dict[str, ReplacementDB] = {}
        for replacement in rows:
            key = replacement.component_type
            if key not in best_by_type or replacement.id > best_by_type[key].id:
                best_by_type[key] = replacement

        return {r.id for r in best_by_type.values()}

    def find_by_vehicle_and_component(
            self,
            vehicle_id: int,
            component_type: ComponentType
    ) -> List[ReplacementDTO]:
        """Найти замены для автомобиля по типу компонента."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value
        ).all()

        return [self._to_dto(replacement) for replacement in db_replacements]

    def find_by_vehicle_component_and_km(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
    ) -> Optional[ReplacementDTO]:
        """Найти замену по автомобилю, типу компонента и пробегу."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value,
            ReplacementDB.km_at_replacement == km,
        ).first()

        if not db_replacement:
            return None

        return self._to_dto(db_replacement)

    def get_last_replacement(
            self,
            vehicle_id: int,
            component_type: ComponentType
    ) -> Optional[ReplacementDTO]:
        """Получить последнюю замену для компонента автомобиля."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        return self._to_dto(db_replacement)

    def find_previous_replacement(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        exclude_id: int,
    ) -> Optional[ReplacementDTO]:
        """Найти предыдущую замену для компонента, исключая указанный ID."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value,
            ReplacementDB.id != exclude_id,
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        return self._to_dto(db_replacement)

    def find_neighbors(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
        exclude_id: int,
    ) -> tuple[Optional[ReplacementDTO], Optional[ReplacementDTO]]:
        """Найти предыдущую (max_km < km) и следующую (min_km > km) замену, исключая указанный ID."""
        base_filter = (
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value,
            ReplacementDB.id != exclude_id,
        )

        prev_row = (
            self.db.query(ReplacementDB)
            .filter(*base_filter, ReplacementDB.km_at_replacement < km)
            .order_by(ReplacementDB.km_at_replacement.desc())
            .first()
        )
        next_row = (
            self.db.query(ReplacementDB)
            .filter(*base_filter, ReplacementDB.km_at_replacement > km)
            .order_by(ReplacementDB.km_at_replacement.asc())
            .first()
        )

        return (
            self._to_dto(prev_row) if prev_row else None,
            self._to_dto(next_row) if next_row else None,
        )

    def get_last_replacement_with_notify(
        self,
        vehicle_id: int,
        component_type: ComponentType,
    ) -> Optional[dict]:
        """Получить последнюю замену с флагами уведомлений для проверки."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        return {
            "id": db_replacement.id,
            "component_type": db_replacement.component_type,
            "component_name": db_replacement.component_name,
            "km_at_replacement": db_replacement.km_at_replacement,
            "interval_km": db_replacement.interval_km,
            "warning_notified": db_replacement.warning_notified,
            "critical_notified": db_replacement.critical_notified,
            "overdue_notified_at_km": db_replacement.overdue_notified_at_km,
            "next_change_date": db_replacement.next_change_date,
            "date_warning_notified": db_replacement.date_warning_notified,
            "date_overdue_notified": db_replacement.date_overdue_notified,
        }

    def get_last_replacements_with_notify(
        self,
        vehicle_id: int,
    ) -> list[dict]:
        """Получить последние замены для всех типов компонентов за один запрос."""
        from sqlalchemy import func, and_

        subq = (
            self.db.query(
                ReplacementDB.component_type,
                func.max(ReplacementDB.km_at_replacement).label('max_km'),
            )
            .filter(ReplacementDB.vehicle_id == vehicle_id)
            .group_by(ReplacementDB.component_type)
            .subquery()
        )

        rows = (
            self.db.query(ReplacementDB)
            .join(
                subq,
                and_(
                    ReplacementDB.component_type == subq.c.component_type,
                    ReplacementDB.km_at_replacement == subq.c.max_km,
                ),
            )
            .filter(ReplacementDB.vehicle_id == vehicle_id)
            .all()
        )

        best_by_type: dict[str, ReplacementDB] = {}
        for replacement in rows:
            key = replacement.component_type
            if key not in best_by_type or replacement.id > best_by_type[key].id:
                best_by_type[key] = replacement

        return [
            {
                "id": replacement.id,
                "component_type": replacement.component_type,
                "km_at_replacement": replacement.km_at_replacement,
                "interval_km": replacement.interval_km,
                "warning_notified": replacement.warning_notified,
                "critical_notified": replacement.critical_notified,
                "overdue_notified_at_km": replacement.overdue_notified_at_km,
            }
            for replacement in best_by_type.values()
        ]

    def update_notify_tracking(
        self,
        replacement_id: int,
        warning_notified: bool | None = None,
        critical_notified: bool | None = None,
        overdue_notified_at_km: int | None = None,
    ) -> None:
        """Обновить флаги отслеживания уведомлений для замены."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if db_replacement:
            if warning_notified is not None:
                db_replacement.warning_notified = warning_notified
            if critical_notified is not None:
                db_replacement.critical_notified = critical_notified
            db_replacement.overdue_notified_at_km = overdue_notified_at_km
            self.db.commit()

    def update_date_notify_tracking(
        self,
        replacement_id: int,
        date_warning_notified: bool | None = None,
        date_overdue_notified: bool | None = None,
    ) -> None:
        """Обновить флаги date-based уведомлений."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if db_replacement:
            if date_warning_notified is not None:
                db_replacement.date_warning_notified = date_warning_notified
            if date_overdue_notified is not None:
                db_replacement.date_overdue_notified = date_overdue_notified
            self.db.commit()

    def delete(self, replacement_id: int) -> bool:
        """Удалить запись о замене."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if db_replacement:
            self.db.delete(db_replacement)
            self.db.commit()
            return True
        return False

    def delete_by_vehicle_id(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все замены для автомобиля. Возвращает количество удалённых."""
        count = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id
        ).delete()
        if commit:
            self.db.commit()
        return count  # type: ignore[no-any-return]

    def get_all(self) -> List[ReplacementDTO]:
        """Получить все замены."""
        db_replacements = self.db.query(ReplacementDB).all()

        return [self._to_dto(replacement) for replacement in db_replacements]
