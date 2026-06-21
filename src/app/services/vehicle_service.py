from sqlalchemy.orm import Session

from app.common.schemas.base_vehicle import VehicleBase
from app.common.models.vehicle import Vehicle
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO


class VehicleService:
    """Класс для работы с авто."""

    def __init__(self, db: Session):
        self.repository = VehicleRepository(db)

    def create(
        self,
        user_id: int,
        vehicle_data: VehicleBase,
    ) -> VehicleDTO:
        """Создать авто."""
        vehicle = Vehicle(
            id=None,
            brand=vehicle_data.brand,
            model=vehicle_data.model,
            plate_number=vehicle_data.plate_number,
            year=vehicle_data.year,
            current_km=vehicle_data.current_km,
            oil_interval_km=vehicle_data.oil_interval_km,
            transmission_interval_km=vehicle_data.transmission_interval_km,
            brake_interval_km=vehicle_data.brake_interval_km,
            coolant_interval_km=vehicle_data.coolant_interval_km,
            power_steering_interval_km=vehicle_data.power_steering_interval_km,
            differential_oil_interval_km=vehicle_data.differential_oil_interval_km,
            owner_id=user_id,
            is_active=True,
        )
        saved = self.repository.save(vehicle)
        return self._to_dto(saved)

    def get_by_plate_number(self, plate_number: str) -> VehicleDTO | None:
        """Получить авто по Рег. номеру."""
        vehicle = self.repository.find_by_plate_number(plate_number)
        return self._to_dto(vehicle) if vehicle else None

    def get_all_active(self) -> list[VehicleDTO]:
        """Получить все активные авто."""
        vehicles = self.repository.find_active()
        return [self._to_dto(v) for v in vehicles]

    def get_all_vehicles(self) -> list[VehicleDTO]:
        """Получить все авто (включая удаленные)."""
        vehicles = self.repository.find_all()
        return [self._to_dto(v) for v in vehicles]

    def get_active_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Получить авто по id."""
        vehicle = self.repository.find_active_by_id(vehicle_id)
        return self._to_dto(vehicle) if vehicle else None

    def get_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Получить авто по id (даже среди удаленных)."""
        vehicle = self.repository.find_by_id(vehicle_id)
        return self._to_dto(vehicle) if vehicle else None

    def update_km(self, vehicle_id: int, new_km: int) -> VehicleDTO | None:
        """Обновить текущий пробег."""
        vehicle = self.repository.find_active_by_id(vehicle_id)
        if not vehicle:
            return None

        if new_km < vehicle.current_km:
            raise ValueError(
                f'Новый пробег {new_km} не может быть меньше текущего {vehicle.current_km}'
            )

        updated = self.repository.update_km(vehicle_id, new_km)
        return self._to_dto(updated) if updated else None

    def update(self, vehicle_data: VehicleDTO) -> VehicleDTO | None:
        """Обновить данные авто."""
        vehicle = Vehicle(
            id=vehicle_data.id,
            brand=vehicle_data.brand,
            model=vehicle_data.model,
            plate_number=vehicle_data.plate_number,
            year=vehicle_data.year,
            current_km=vehicle_data.current_km,
            is_active=vehicle_data.is_active,
            oil_interval_km=vehicle_data.oil_interval_km,
            transmission_interval_km=vehicle_data.transmission_interval_km,
            brake_interval_km=vehicle_data.brake_interval_km,
            coolant_interval_km=vehicle_data.coolant_interval_km,
            power_steering_interval_km=vehicle_data.power_steering_interval_km,
            differential_oil_interval_km=vehicle_data.differential_oil_interval_km,
        )
        updated = self.repository.save(vehicle)
        return self._to_dto(updated) if updated else None

    def delete(self, vehicle_id: int) -> bool:
        """Удалить автомобиль."""
        return bool(self.repository.delete(vehicle_id))

    def hard_delete(self, vehicle_id: int) -> bool:
        """Полностью удалить автомобиль из БД."""
        return self.repository.hard_delete(vehicle_id)  # type: ignore[no-any-return]

    def get_all_active_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить активные авто только для пользователя."""
        vehicles = self.repository.find_active_by_owner(user_id)
        return [self._to_dto(v) for v in vehicles]

    def get_all_vehicles_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить все авто пользователя (включая удалённые)."""
        vehicles = self.repository.find_by_owner(user_id)
        return [self._to_dto(v) for v in vehicles]

    def _to_dto(self, vehicle: Vehicle) -> VehicleDTO:
        return VehicleDTO(
            id=vehicle.id,
            brand=vehicle.brand,
            model=vehicle.model,
            plate_number=vehicle.plate_number,
            year=vehicle.year,
            current_km=vehicle.current_km,
            is_active=vehicle.is_active,
            owner_id=vehicle.owner_id,
            oil_interval_km=vehicle.oil_interval_km,
            transmission_interval_km=vehicle.transmission_interval_km,
            brake_interval_km=vehicle.brake_interval_km,
            coolant_interval_km=vehicle.coolant_interval_km,
            power_steering_interval_km=vehicle.power_steering_interval_km,
            differential_oil_interval_km=vehicle.differential_oil_interval_km,
        )
