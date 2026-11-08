from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from app.api.fuel_record.schema import FuelRecordCreateRequest
from app.repository.fuel_record_repository import FuelRecordRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import FuelRecordDTO, VehicleDTO

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль не найден'
_MSG_FUTURE_DATE = 'Дата заправки не может быть позже сегодняшнего дня'
_MSG_NEGATIVE_KM = 'Пробег не может быть отрицательным'
_MSG_NON_POSITIVE_LITERS = 'Объём топлива должен быть больше 0'
_MSG_NEGATIVE_COST = 'Стоимость заправки не может быть отрицательной'


class FuelRecordService:
    """Класс для работы с заправками."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = FuelRecordRepository(db)
        self.vehicle_repository = VehicleRepository(db)

    @staticmethod
    def _validate_date(fuel_date: date) -> None:
        if fuel_date > date.today():
            raise ValueError(_MSG_FUTURE_DATE)

    @staticmethod
    def _validate_km(km_at_fuel: int) -> None:
        if km_at_fuel < 0:
            raise ValueError(_MSG_NEGATIVE_KM)

    @staticmethod
    def _validate_liters(liters: float) -> None:
        if liters <= 0:
            raise ValueError(_MSG_NON_POSITIVE_LITERS)

    @staticmethod
    def _validate_cost(total_cost: int) -> None:
        if total_cost < 0:
            raise ValueError(_MSG_NEGATIVE_COST)

    @staticmethod
    def _with_consumption(records: list[FuelRecordDTO]) -> list[FuelRecordDTO]:
        """Рассчитать расход л/100 км между соседними заправками по пробегу."""
        ordered = sorted(
            records,
            key=lambda record: (
                record.km_at_fuel,
                record.fuel_date,
                record.id or 0,
            ),
        )

        consumption: dict[int | None, float | None] = {}
        previous: FuelRecordDTO | None = None
        for record in ordered:
            value = None
            if previous is not None:
                delta_km = record.km_at_fuel - previous.km_at_fuel
                if delta_km > 0:
                    value = round(record.liters / delta_km * 100, 2)
            consumption[record.id] = value
            previous = record

        return [
            replace(record, consumption_l_per_100km=consumption.get(record.id))
            for record in records
        ]

    def create(
        self,
        vehicle_id: int,
        request: FuelRecordCreateRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
    ) -> FuelRecordDTO:
        """Создать запись о заправке."""
        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND)

        self._validate_date(request.fuel_date)
        self._validate_km(request.km_at_fuel)
        self._validate_liters(request.liters)
        self._validate_cost(request.total_cost)

        record = FuelRecordDTO(
            id=None,
            vehicle_id=vehicle_id,
            fuel_date=request.fuel_date,
            km_at_fuel=request.km_at_fuel,
            liters=round(request.liters, 3),
            total_cost=request.total_cost,
        )

        saved = self.repository.save(record, commit=False)
        self._update_vehicle_km(vehicle_dto, request.km_at_fuel)

        if commit:
            self.db.commit()

        return self.get_by_id(saved.id) if saved.id else saved  # type: ignore[return-value]

    def get_by_id(self, record_id: int) -> FuelRecordDTO | None:
        """Получить заправку по id с рассчитанным расходом."""
        record = self.repository.find_by_id(record_id)
        if not record:
            return None

        records = self._with_consumption(
            self.repository.find_by_vehicle_id(record.vehicle_id)
        )
        return next((item for item in records if item.id == record_id), record)

    def get_by_vehicle(self, vehicle_id: int) -> list[FuelRecordDTO]:
        """Получить заправки автомобиля с рассчитанным расходом."""
        return self._with_consumption(
            self.repository.find_by_vehicle_id(vehicle_id)
        )

    def update(
        self,
        record_id: int,
        *,
        fuel_date: date | None = None,
        km_at_fuel: int | None = None,
        liters: float | None = None,
        total_cost: int | None = None,
        commit: bool = True,
    ) -> FuelRecordDTO | None:
        """Частично обновить запись о заправке."""
        record = self.repository.find_by_id(record_id)
        if not record:
            return None

        if fuel_date is not None:
            self._validate_date(fuel_date)
            record.fuel_date = fuel_date
        if km_at_fuel is not None:
            self._validate_km(km_at_fuel)
            record.km_at_fuel = km_at_fuel
        if liters is not None:
            self._validate_liters(liters)
            record.liters = round(liters, 3)
        if total_cost is not None:
            self._validate_cost(total_cost)
            record.total_cost = total_cost

        self.repository.save(record, commit=False)

        vehicle_dto = self.vehicle_repository.find_active_by_id(record.vehicle_id)
        if vehicle_dto:
            self._update_vehicle_km(vehicle_dto, record.km_at_fuel)

        if commit:
            self.db.commit()

        return self.get_by_id(record_id)

    def delete(self, record_id: int) -> bool:
        """Удалить запись о заправке."""
        return bool(self.repository.delete(record_id))

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все заправки автомобиля."""
        return self.repository.delete_by_vehicle_id(vehicle_id, commit)  # type: ignore[no-any-return]

    def _update_vehicle_km(self, vehicle_dto: VehicleDTO, km_at_fuel: int) -> None:
        if km_at_fuel > vehicle_dto.current_km:
            vehicle_dto.current_km = km_at_fuel
            self.vehicle_repository.save(vehicle_dto, commit=False)
