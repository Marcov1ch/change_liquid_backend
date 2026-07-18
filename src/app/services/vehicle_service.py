from sqlalchemy.orm import Session

from app.common.schemas.base_vehicle import VehicleBase
from app.repository.enum_repository import EnumRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO


class VehicleService:
    """Класс для работы с авто."""

    def __init__(self, db: Session):
        self.repository = VehicleRepository(db)
        self.enum_repo = EnumRepository(db)

    def create(
        self,
        user_id: int,
        vehicle_data: VehicleBase,
    ) -> VehicleDTO:
        """Создать авто."""
        brand = self.enum_repo.get_brand_by_name(vehicle_data.brand)
        if not brand:
            raise ValueError(f'Brand "{vehicle_data.brand}" not found')

        models = self.enum_repo.get_models_by_brand(vehicle_data.brand)
        model = next((m for m in models if m.name == vehicle_data.model), None)
        if not model:
            raise ValueError(f'Model "{vehicle_data.model}" not found for brand "{vehicle_data.brand}"')

        intervals = {}
        notify_flags = {}
        if hasattr(vehicle_data, 'intervals'):
            intervals = vehicle_data.intervals
        if hasattr(vehicle_data, 'notify_flags'):
            notify_flags = vehicle_data.notify_flags

        dto = VehicleDTO(
            id=None,
            brand=vehicle_data.brand,
            model=vehicle_data.model,
            brand_id=brand.id,
            model_id=model.id,
            plate_number=vehicle_data.plate_number,
            year=vehicle_data.year,
            current_km=vehicle_data.current_km,
            is_active=True,
            owner_id=user_id,
            intervals=intervals,
            notify_flags=notify_flags,
        )

        return self.repository.save(dto)

    def get_by_plate_number(self, plate_number: str) -> VehicleDTO | None:
        """Получить авто по Рег. номеру."""
        return self.repository.find_by_plate_number(plate_number)

    def get_all_active(self) -> list[VehicleDTO]:
        """Получить все активные авто."""
        return self.repository.find_active()  # type: ignore[no-any-return]

    def get_all_vehicles(self) -> list[VehicleDTO]:
        """Получить все авто (включая удаленные)."""
        return self.repository.find_all()  # type: ignore[no-any-return]

    def get_active_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Получить активное авто по id."""
        return self.repository.find_active_by_id(vehicle_id)

    def get_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Получить авто по id (даже среди удаленных)."""
        return self.repository.find_by_id(vehicle_id)

    def validate_km_not_below_replacements(self, vehicle_id: int, new_km: int) -> None:
        """Проверить, что пробег не ниже максимального пробега замен."""
        max_km = self.repository.get_max_replacement_km(vehicle_id)
        if new_km < max_km:
            raise ValueError(
                f'Пробег {new_km} км не может быть меньше максимального пробега замен ({max_km} км)'
            )

    def update_km(self, vehicle_id: int, new_km: int) -> VehicleDTO | None:
        """Обновить текущий пробег."""
        dto = self.repository.find_active_by_id(vehicle_id)
        if not dto:
            return None

        self.validate_km_not_below_replacements(vehicle_id, new_km)

        if new_km < dto.current_km:
            raise ValueError(
                f'Новый пробег {new_km} не может быть меньше текущего {dto.current_km}'
            )

        return self.repository.update_km(vehicle_id, new_km)

    def update(self, dto: VehicleDTO) -> VehicleDTO | None:
        """Обновить данные авто."""
        return self.repository.save(dto)

    def update_brand_model(
        self,
        dto: VehicleDTO,
        brand: str | None,
        model: str | None,
    ) -> VehicleDTO:
        """Обновить марку/модель на DTO с резолвом brand_id/model_id."""
        current_brand = brand if brand is not None else dto.brand

        if brand is not None:
            brand_obj = self.enum_repo.get_brand_by_name(brand)
            if not brand_obj:
                raise ValueError(f'Brand "{brand}" not found')
            dto.brand = brand
            dto.brand_id = brand_obj.id

        if model is not None:
            models = self.enum_repo.get_models_by_brand(current_brand)
            model_obj = next((m for m in models if m.name == model), None)
            if not model_obj:
                raise ValueError(
                    f'Model "{model}" not found for brand "{current_brand}"'
                )
            dto.model = model
            dto.model_id = model_obj.id

        return dto

    def delete(self, vehicle_id: int) -> bool:
        """Удалить автомобиль."""
        return bool(self.repository.delete(vehicle_id))

    def hard_delete(self, vehicle_id: int) -> bool:
        """Полностью удалить автомобиль из БД."""
        return self.repository.hard_delete(vehicle_id)  # type: ignore[no-any-return]

    def get_all_active_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить активные авто только для пользователя."""
        return self.repository.find_active_by_owner(user_id)  # type: ignore[no-any-return]

    def get_all_vehicles_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить все авто пользователя (включая удалённые)."""
        return self.repository.find_by_owner(user_id)  # type: ignore[no-any-return]
