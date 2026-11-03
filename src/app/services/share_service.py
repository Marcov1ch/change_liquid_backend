import secrets
from typing import cast

from sqlalchemy.orm import Session

from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO


class VehicleShareService:
    """Бизнес-логика публичного шаринга авто."""

    def __init__(self, db: Session):
        self.repository = VehicleRepository(db)

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    def get_token(self, vehicle_id: int) -> str | None:
        """Получить текущий токен авто."""
        vehicle = self.repository.find_by_id(vehicle_id)
        return cast(str | None, vehicle.share_token) if vehicle else None

    def enable(self, vehicle_id: int) -> str | None:
        """Включить шаринг, сохранив существующий токен."""
        vehicle = self.repository.find_by_id(vehicle_id)
        if not vehicle:
            return None
        if vehicle.share_token:
            return cast(str, vehicle.share_token)
        token = self._generate_token()
        self.repository.set_share_token(vehicle_id, token)
        return token

    def rotate(self, vehicle_id: int) -> str | None:
        """Перевыпустить токен, инвалидируя старую ссылку."""
        vehicle = self.repository.find_by_id(vehicle_id)
        if not vehicle:
            return None
        token = self._generate_token()
        self.repository.set_share_token(vehicle_id, token)
        return token

    def disable(self, vehicle_id: int) -> bool:
        """Отключить шаринг и инвалидировать ссылку."""
        return bool(self.repository.set_share_token(vehicle_id, None))

    def find_by_token(self, token: str) -> VehicleDTO | None:
        """Найти авто по публичному токену."""
        return self.repository.find_by_share_token(token)
