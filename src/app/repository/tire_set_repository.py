from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import TireSetDB
from app.services.dto import TireSetDTO


class TireSetRepository:
    """Репозиторий для работы с комплектами шин в БД."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_row: TireSetDB, current_km: int | None = None) -> TireSetDTO:
        """Конвертировать ORM-модель в DTO с расчётом суммарного пробега."""
        total_km = db_row.accumulated_km
        if (
            db_row.is_installed
            and db_row.installed_km is not None
            and current_km is not None
        ):
            total_km += max(0, current_km - db_row.installed_km)

        return TireSetDTO(
            id=db_row.id,
            vehicle_id=db_row.vehicle_id,
            name=db_row.name,
            season=db_row.season,
            purchase_date=db_row.purchase_date,
            purchase_price=db_row.purchase_price,
            accumulated_km=db_row.accumulated_km,
            installed_km=db_row.installed_km,
            installed_date=db_row.installed_date,
            is_installed=bool(db_row.is_installed),
            created_at=db_row.created_at,
            total_km=total_km,
        )

    @staticmethod
    def _to_orm_data(tire_set: TireSetDTO) -> dict:
        """Преобразовать DTO в dict для ORM."""
        return {
            'vehicle_id': tire_set.vehicle_id,
            'name': tire_set.name,
            'season': tire_set.season,
            'purchase_date': tire_set.purchase_date,
            'purchase_price': tire_set.purchase_price,
            'accumulated_km': tire_set.accumulated_km,
            'installed_km': tire_set.installed_km,
            'installed_date': tire_set.installed_date,
            'is_installed': tire_set.is_installed,
        }

    def save(
        self,
        tire_set: TireSetDTO,
        current_km: int | None = None,
        commit: bool = True,
    ) -> TireSetDTO:
        """Создать или обновить комплект шин."""
        if tire_set.id:
            db_tire_set = self.db.query(TireSetDB).filter(
                TireSetDB.id == tire_set.id
            ).first()
            if not db_tire_set:
                raise ValueError(f'TireSet with id {tire_set.id} not found')

            for key, value in self._to_orm_data(tire_set).items():
                setattr(db_tire_set, key, value)
        else:
            db_tire_set = TireSetDB(**self._to_orm_data(tire_set))
            self.db.add(db_tire_set)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_tire_set)

        return self._to_dto(db_tire_set, current_km)

    def find_by_id(
        self,
        tire_set_id: int,
        current_km: int | None = None,
    ) -> Optional[TireSetDTO]:
        """Найти комплект шин по id."""
        db_tire_set = self.db.query(TireSetDB).filter(
            TireSetDB.id == tire_set_id
        ).first()
        if not db_tire_set:
            return None
        return self._to_dto(db_tire_set, current_km)

    def find_by_vehicle(
        self,
        vehicle_id: int,
        current_km: int | None = None,
    ) -> List[TireSetDTO]:
        """Найти все комплекты шин автомобиля."""
        db_tire_sets = self.db.query(TireSetDB).filter(
            TireSetDB.vehicle_id == vehicle_id,
        ).order_by(TireSetDB.is_installed.desc(), TireSetDB.id.asc()).all()
        return [self._to_dto(item, current_km) for item in db_tire_sets]

    def find_installed(
        self,
        vehicle_id: int,
        current_km: int | None = None,
    ) -> Optional[TireSetDTO]:
        """Найти установленный комплект шин автомобиля."""
        db_tire_set = self.db.query(TireSetDB).filter(
            TireSetDB.vehicle_id == vehicle_id,
            TireSetDB.is_installed.is_(True),
        ).first()
        if not db_tire_set:
            return None
        return self._to_dto(db_tire_set, current_km)

    def delete(self, tire_set_id: int, commit: bool = True) -> bool:
        """Удалить комплект шин."""
        db_tire_set = self.db.query(TireSetDB).filter(
            TireSetDB.id == tire_set_id
        ).first()
        if db_tire_set:
            self.db.delete(db_tire_set)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return True
        return False

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все комплекты шин автомобиля."""
        count = self.db.query(TireSetDB).filter(
            TireSetDB.vehicle_id == vehicle_id,
        ).delete()
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return count  # type: ignore[no-any-return]
