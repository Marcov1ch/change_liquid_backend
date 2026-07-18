from sqlalchemy.orm import Session
from app.db.models import ReplacementDB
from app.common.models.replacement import Replacement
from app.common.enums import ComponentType
from typing import List, Optional


class ReplacementRepository:
    """Репозиторий для работы с заменами в БД."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, replacement: Replacement) -> Replacement:
        """Создать или обновить запись о замене."""
        if replacement.id:
            db_replacement = self.db.query(ReplacementDB).filter(
                ReplacementDB.id == replacement.id
            ).first()
            if not db_replacement:
                raise ValueError(f'Replacement with id {replacement.id} not found')

            update_data = replacement.model_dump(exclude={'id'})
            if 'component_type' in update_data and update_data['component_type']:
                update_data['component_type'] = update_data['component_type'].value
            for key, value in update_data.items():
                setattr(db_replacement, key, value)
        else:
            replacement_data = replacement.model_dump(exclude={'id'})
            if replacement_data.get('component_type'):
                replacement_data['component_type'] = replacement_data['component_type'].value
            db_replacement = ReplacementDB(**replacement_data)
            self.db.add(db_replacement)

        self.db.commit()
        self.db.refresh(db_replacement)

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('component_type'):
            result_dict['component_type'] = ComponentType(result_dict['component_type'])
        return Replacement(**result_dict)

    def find_by_id(self, replacement_id: int) -> Optional[Replacement]:
        """Найти замену по id."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('component_type'):
            result_dict['component_type'] = ComponentType(result_dict['component_type'])
        return Replacement(**result_dict)

    def find_by_vehicle_ids(self, vehicle_ids: list[int]) -> List[Replacement]:
        """Найти все замены для списка автомобилей."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id.in_(vehicle_ids)
        ).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            result_dict.pop('_sa_instance_state', None)
            result_dict.pop('warning_notified', None)
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('component_type'):
                result_dict['component_type'] = ComponentType(result_dict['component_type'])
            result.append(Replacement(**result_dict))
        return result

    def find_by_vehicle_id(self, vehicle_id: int) -> List[Replacement]:
        """Найти все замены для автомобиля."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id
        ).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('component_type'):
                result_dict['component_type'] = ComponentType(result_dict['component_type'])
            result.append(Replacement(**result_dict))
        return result

    def find_by_vehicle_and_component(
            self,
            vehicle_id: int,
            component_type: ComponentType
    ) -> List[Replacement]:
        """Найти замены для автомобиля по типу компонента."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value
        ).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('component_type'):
                result_dict['component_type'] = ComponentType(result_dict['component_type'])
            result.append(Replacement(**result_dict))
        return result

    def find_by_vehicle_component_and_km(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
    ) -> Optional[Replacement]:
        """Найти замену по автомобилю, типу компонента и пробегу."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value,
            ReplacementDB.km_at_replacement == km,
        ).first()

        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('component_type'):
            result_dict['component_type'] = ComponentType(result_dict['component_type'])
        return Replacement(**result_dict)

    def get_last_replacement(
            self,
            vehicle_id: int,
            component_type: ComponentType
    ) -> Optional[Replacement]:
        """Получить последнюю замену для компонента автомобиля."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('component_type'):
            result_dict['component_type'] = ComponentType(result_dict['component_type'])
        return Replacement(**result_dict)

    def find_previous_replacement(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        exclude_id: int,
    ) -> Optional[Replacement]:
        """Найти предыдущую замену для компонента, исключая указанный ID."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.component_type == component_type.value,
            ReplacementDB.id != exclude_id,
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('component_type'):
            result_dict['component_type'] = ComponentType(result_dict['component_type'])
        return Replacement(**result_dict)

    def find_neighbors(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
        exclude_id: int,
    ) -> tuple[Optional[Replacement], Optional[Replacement]]:
        """Найти предыдущую (max_km < km) и следующую (min_km > km) замену, исключая указанный ID."""
        def _to_replacement(db_row: ReplacementDB) -> Replacement:
            result_dict = db_row.__dict__.copy()
            result_dict.pop('_sa_instance_state', None)
            result_dict.pop('warning_notified', None)
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('component_type'):
                result_dict['component_type'] = ComponentType(result_dict['component_type'])
            return Replacement(**result_dict)

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
            _to_replacement(prev_row) if prev_row else None,
            _to_replacement(next_row) if next_row else None,
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
            "km_at_replacement": db_replacement.km_at_replacement,
            "interval_km": db_replacement.interval_km,
            "warning_notified": db_replacement.warning_notified,
            "critical_notified": db_replacement.critical_notified,
            "overdue_notified_at_km": db_replacement.overdue_notified_at_km,
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
        for r in rows:
            key = r.component_type
            if key not in best_by_type or r.id > best_by_type[key].id:
                best_by_type[key] = r

        return [
            {
                "id": r.id,
                "component_type": r.component_type,
                "km_at_replacement": r.km_at_replacement,
                "interval_km": r.interval_km,
                "warning_notified": r.warning_notified,
                "critical_notified": r.critical_notified,
                "overdue_notified_at_km": r.overdue_notified_at_km,
            }
            for r in best_by_type.values()
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

    def delete_by_vehicle_id(self, vehicle_id: int) -> int:
        """Удалить все замены для автомобиля. Возвращает количество удалённых."""
        count = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id
        ).delete()
        self.db.commit()
        return count  # type: ignore[no-any-return]

    def get_all(self) -> List[Replacement]:
        """Получить все замены."""
        db_replacements = self.db.query(ReplacementDB).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            if result_dict.get('component_type'):
                result_dict['component_type'] = ComponentType(result_dict['component_type'])
            result.append(Replacement(**result_dict))
        return result
