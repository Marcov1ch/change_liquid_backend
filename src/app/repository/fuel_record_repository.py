from sqlalchemy.orm import Session

from app.db.models import FuelRecordDB
from app.services.dto import FuelRecordDTO


class FuelRecordRepository:
    """Репозиторий для работы с заправками."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_record: FuelRecordDB) -> FuelRecordDTO:
        """Преобразовать ORM-модель в DTO."""
        return FuelRecordDTO(
            id=db_record.id,
            vehicle_id=db_record.vehicle_id,
            fuel_date=db_record.fuel_date,
            km_at_fuel=db_record.km_at_fuel,
            liters=db_record.liters,
            total_cost=db_record.total_cost,
        )

    def save(self, record: FuelRecordDTO, commit: bool = True) -> FuelRecordDTO:
        """Создать или обновить запись о заправке."""
        if record.id:
            db_record = self.db.query(FuelRecordDB).filter(
                FuelRecordDB.id == record.id
            ).first()
            if not db_record:
                raise ValueError(f'FuelRecord with id {record.id} not found')

            db_record.vehicle_id = record.vehicle_id
            db_record.fuel_date = record.fuel_date
            db_record.km_at_fuel = record.km_at_fuel
            db_record.liters = record.liters
            db_record.total_cost = record.total_cost
        else:
            db_record = FuelRecordDB(
                vehicle_id=record.vehicle_id,
                fuel_date=record.fuel_date,
                km_at_fuel=record.km_at_fuel,
                liters=record.liters,
                total_cost=record.total_cost,
            )
            self.db.add(db_record)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_record)

        return self._to_dto(db_record)

    def find_by_id(self, record_id: int) -> FuelRecordDTO | None:
        """Найти заправку по id."""
        db_record = self.db.query(FuelRecordDB).filter(
            FuelRecordDB.id == record_id
        ).first()
        return self._to_dto(db_record) if db_record else None

    def find_by_vehicle_id(self, vehicle_id: int) -> list[FuelRecordDTO]:
        """Найти все заправки автомобиля (сначала новые)."""
        db_records = self.db.query(FuelRecordDB).filter(
            FuelRecordDB.vehicle_id == vehicle_id
        ).order_by(
            FuelRecordDB.fuel_date.desc(),
            FuelRecordDB.id.desc(),
        ).all()
        return [self._to_dto(record) for record in db_records]

    def delete(self, record_id: int, commit: bool = True) -> bool:
        """Удалить запись о заправке."""
        db_record = self.db.query(FuelRecordDB).filter(
            FuelRecordDB.id == record_id
        ).first()
        if db_record:
            self.db.delete(db_record)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return True
        return False

    def delete_by_vehicle_id(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все заправки автомобиля. Возвращает количество удалённых."""
        count = self.db.query(FuelRecordDB).filter(
            FuelRecordDB.vehicle_id == vehicle_id
        ).delete()
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return count  # type: ignore[no-any-return]
