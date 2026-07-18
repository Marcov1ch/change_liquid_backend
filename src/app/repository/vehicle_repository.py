from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ReplacementDB, VehicleDB
from app.services.dto import VehicleDTO
from app.common.component_config import COMPONENTS_CONFIG


class VehicleRepository:
    """Репозиторий для работы с автомобилями в БД."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_vehicle: VehicleDB) -> VehicleDTO:
        """Преобразовать ORM-модель в DTO."""
        intervals: dict[str, int] = {}
        notify_flags: dict[str, bool] = {}
        for cfg in COMPONENTS_CONFIG:
            intervals[cfg.type.value] = getattr(db_vehicle, cfg.interval_field)
            notify_flags[cfg.type.value] = getattr(db_vehicle, cfg.notify_field)
        return VehicleDTO(
            id=db_vehicle.id,
            brand=db_vehicle.brand_ref.name,
            model=db_vehicle.model_ref.name,
            brand_id=db_vehicle.brand_id,
            model_id=db_vehicle.model_id,
            plate_number=db_vehicle.plate_number,
            year=db_vehicle.year,
            current_km=db_vehicle.current_km,
            is_active=db_vehicle.is_active,
            owner_id=db_vehicle.owner_id,
            intervals=intervals,
            notify_flags=notify_flags,
        )

    def _apply_intervals(self, db_vehicle: VehicleDB, dto: VehicleDTO) -> None:
        """Записать значения интервалов и флагов из DTO в ORM-модель."""
        for cfg in COMPONENTS_CONFIG:
            setattr(db_vehicle, cfg.interval_field, dto.intervals.get(cfg.type.value, cfg.default_interval))
            setattr(db_vehicle, cfg.notify_field, dto.notify_flags.get(cfg.type.value, True))

    def save(self, dto: VehicleDTO) -> VehicleDTO:
        """Создать или обновить запись об автомобиле."""
        if dto.id:
            db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == dto.id).first()
            if not db_vehicle:
                raise ValueError(f'Vehicle with id {dto.id} not found')

            db_vehicle.brand_id = dto.brand_id
            db_vehicle.model_id = dto.model_id
            db_vehicle.plate_number = dto.plate_number
            db_vehicle.year = dto.year
            db_vehicle.current_km = dto.current_km
            db_vehicle.is_active = dto.is_active
            db_vehicle.owner_id = dto.owner_id
            self._apply_intervals(db_vehicle, dto)
        else:
            db_vehicle = VehicleDB(
                brand_id=dto.brand_id,
                model_id=dto.model_id,
                plate_number=dto.plate_number,
                year=dto.year,
                current_km=dto.current_km,
                is_active=dto.is_active,
                owner_id=dto.owner_id,
            )
            self._apply_intervals(db_vehicle, dto)
            self.db.add(db_vehicle)

        self.db.commit()
        self.db.refresh(db_vehicle)

        return self._to_dto(db_vehicle)

    def find_by_plate_number(self, plate_number: str) -> VehicleDTO | None:
        """Найти авто по Рег. номеру."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.plate_number == plate_number).first()
        return self._to_dto(db_vehicle) if db_vehicle else None

    def find_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Найти авто по id (включая удаленные)."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        return self._to_dto(db_vehicle) if db_vehicle else None

    def find_active(self) -> list[VehicleDTO]:
        """Получить все активные авто."""
        db_vehicles = self.db.query(VehicleDB).filter(VehicleDB.is_active).all()
        return [self._to_dto(v) for v in db_vehicles]

    def find_all(self) -> list[VehicleDTO]:
        """Получить все авто (включая удаленные)."""
        db_vehicles = self.db.query(VehicleDB).all()
        return [self._to_dto(v) for v in db_vehicles]

    def find_active_by_id(self, vehicle_id: int) -> VehicleDTO | None:
        """Найти активное авто по id."""
        db_vehicle = self.db.query(VehicleDB).filter(
            VehicleDB.id == vehicle_id, VehicleDB.is_active
        ).first()
        return self._to_dto(db_vehicle) if db_vehicle else None

    def get_max_replacement_km(self, vehicle_id: int) -> int:
        """Максимальный пробег среди всех замен для авто."""
        result = self.db.query(func.max(ReplacementDB.km_at_replacement)).filter(
            ReplacementDB.vehicle_id == vehicle_id,
        ).scalar()
        return result or 0

    def update_km(self, vehicle_id: int, new_km: int) -> VehicleDTO | None:
        """Обновить пробег автомобиля."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            db_vehicle.current_km = new_km
            self.db.commit()
            self.db.refresh(db_vehicle)
            return self._to_dto(db_vehicle)
        return None

    def delete(self, vehicle_id: int) -> bool:
        """Мягкое удаление авто (is_active = False)."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            db_vehicle.is_active = False
            self.db.commit()
            return True
        return False

    def hard_delete(self, vehicle_id: int) -> bool:
        """Полное удаление авто из БД."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            self.db.delete(db_vehicle)
            self.db.commit()
            return True
        return False

    def find_active_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить активные авто пользователя."""
        db_vehicles = self.db.query(VehicleDB).filter(
            VehicleDB.owner_id == user_id,
            VehicleDB.is_active
        ).all()
        return [self._to_dto(v) for v in db_vehicles]

    def find_by_owner(self, user_id: int) -> list[VehicleDTO]:
        """Получить все авто пользователя (включая удаленные)."""
        db_vehicles = self.db.query(VehicleDB).filter(
            VehicleDB.owner_id == user_id
        ).all()
        return [self._to_dto(v) for v in db_vehicles]

    def find_all_active_with_owner(self) -> list[dict]:
        """Получить все активные авто с информацией о владельце для уведомлений."""
        from sqlalchemy.orm import joinedload
        db_vehicles = self.db.query(VehicleDB).options(
            joinedload(VehicleDB.owner),
            joinedload(VehicleDB.brand_ref),
            joinedload(VehicleDB.model_ref),
        ).filter(VehicleDB.is_active).all()

        result = []
        for v in db_vehicles:
            intervals: dict[str, int] = {}
            notify_flags: dict[str, bool] = {}
            for cfg in COMPONENTS_CONFIG:
                intervals[cfg.type.value] = getattr(v, cfg.interval_field)
                notify_flags[cfg.type.value] = getattr(v, cfg.notify_field)
            result.append({
                "id": v.id,
                "brand": v.brand_ref.name,
                "model": v.model_ref.name,
                "plate_number": v.plate_number,
                "current_km": v.current_km,
                "intervals": intervals,
                "notify_flags": notify_flags,
                "owner_email": v.owner.email if v.owner else "",
                "owner_username": v.owner.username if v.owner else "",
            })
        return result
