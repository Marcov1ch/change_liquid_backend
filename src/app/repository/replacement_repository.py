from sqlalchemy.orm import Session
from app.db.models import ReplacementDB
from app.common.models.liquid import Liquid
from app.common.enums import LiquidType
from typing import List, Optional


class ReplacementRepository:
    """Репозиторий для работы с заменами жидкостей."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, replacement: Liquid) -> Liquid:
        """Сохранить или обновить замену."""
        if replacement.id:
            db_replacement = self.db.query(ReplacementDB).filter(
                ReplacementDB.id == replacement.id
            ).first()
            if not db_replacement:
                raise ValueError(f'Replacement with id {replacement.id} not found')

            update_data = replacement.model_dump(exclude={'id'})
            # Преобразуем Enum в строку
            if 'liquid_type' in update_data and update_data['liquid_type']:
                update_data['liquid_type'] = update_data['liquid_type'].value
            for key, value in update_data.items():
                setattr(db_replacement, key, value)
        else:
            replacement_data = replacement.model_dump(exclude={'id'})
            # Преобразуем Enum в строку
            if replacement_data.get('liquid_type'):
                replacement_data['liquid_type'] = replacement_data['liquid_type'].value
            db_replacement = ReplacementDB(**replacement_data)
            self.db.add(db_replacement)

        self.db.commit()
        self.db.refresh(db_replacement)

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('liquid_type'):
            result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
        return Liquid(**result_dict)

    def find_by_id(self, replacement_id: int) -> Optional[Liquid]:
        """Найти замену по ID."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('liquid_type'):
            result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
        return Liquid(**result_dict)

    def find_by_vehicle_id(self, vehicle_id: int) -> List[Liquid]:
        """Найти все замены для автомобиля."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id
        ).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('liquid_type'):
                result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
            result.append(Liquid(**result_dict))
        return result

    def find_by_vehicle_and_liquid(
            self,
            vehicle_id: int,
            liquid_type: LiquidType
    ) -> List[Liquid]:
        """Найти замены конкретной жидкости для авто."""
        db_replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.liquid_type == liquid_type.value
        ).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            result_dict.pop('critical_notified', None)
            result_dict.pop('overdue_notified_at_km', None)
            if result_dict.get('liquid_type'):
                result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
            result.append(Liquid(**result_dict))
        return result

    def get_last_replacement(
            self,
            vehicle_id: int,
            liquid_type: LiquidType
    ) -> Optional[Liquid]:
        """Получить последнюю замену для жидкости."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.liquid_type == liquid_type.value
        ).order_by(ReplacementDB.km_at_replacement.desc()).first()

        if not db_replacement:
            return None

        result_dict = db_replacement.__dict__.copy()
        result_dict.pop('warning_notified', None)
        result_dict.pop('critical_notified', None)
        result_dict.pop('overdue_notified_at_km', None)
        if result_dict.get('liquid_type'):
            result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
        return Liquid(**result_dict)

    def get_last_replacement_with_notify(
        self,
        vehicle_id: int,
        liquid_type: LiquidType,
    ) -> Optional[dict]:
        """Получить последнюю замену с полями уведомлений."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id == vehicle_id,
            ReplacementDB.liquid_type == liquid_type.value
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

    def update_notify_tracking(
        self,
        replacement_id: int,
        warning_notified: bool | None = None,
        critical_notified: bool | None = None,
        overdue_notified_at_km: int | None = None,
    ) -> None:
        """Обновить флаги отслеживания уведомлений."""
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
        """Удалить замену."""
        db_replacement = self.db.query(ReplacementDB).filter(
            ReplacementDB.id == replacement_id
        ).first()
        if db_replacement:
            self.db.delete(db_replacement)
            self.db.commit()
            return True
        return False

    def get_all(self) -> List[Liquid]:
        """Получить все замены."""
        db_replacements = self.db.query(ReplacementDB).all()

        result = []
        for r in db_replacements:
            result_dict = r.__dict__.copy()
            if result_dict.get('liquid_type'):
                result_dict['liquid_type'] = LiquidType(result_dict['liquid_type'])
            result.append(Liquid(**result_dict))
        return result
