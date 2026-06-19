from sqlalchemy.orm import Session

from app.common.enums import BrandCar
from app.db.models import VehicleDB
from app.common.models.vehicle import Vehicle


class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, vehicle: Vehicle) -> Vehicle:
        """Сохранить или обновить."""
        if vehicle.id:
            db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle.id).first()
            if not db_vehicle:
                raise ValueError(f'Vehicle with id {vehicle.id} not found')

            update_data = vehicle.model_dump(exclude={'id'})
            if 'brand' in update_data and update_data['brand']:
                update_data['brand'] = update_data['brand'].value
            for key, value in update_data.items():
                setattr(db_vehicle, key, value)
        else:
            vehicle_data = vehicle.model_dump(exclude={'id'})
            if vehicle_data.get('brand'):
                vehicle_data['brand'] = vehicle_data['brand'].value
            db_vehicle = VehicleDB(**vehicle_data)
            self.db.add(db_vehicle)

        self.db.commit()
        self.db.refresh(db_vehicle)

        result_dict = db_vehicle.__dict__.copy()
        if result_dict.get('brand'):
            result_dict['brand'] = BrandCar(result_dict['brand'])
        return Vehicle(**result_dict)

    def find_by_plate_number(self, plate_number: str) -> Vehicle | None:
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.plate_number == plate_number).first()
        return Vehicle(**db_vehicle.__dict__) if db_vehicle else None

    def find_by_id(self, vehicle_id: int) -> Vehicle | None:
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        return Vehicle(**db_vehicle.__dict__) if db_vehicle else None

    def find_active(self) -> list[Vehicle]:
        db_vehicles = self.db.query(VehicleDB).filter(VehicleDB.is_active).all()
        return [Vehicle(**v.__dict__) for v in db_vehicles]

    def find_all(self) -> list[Vehicle]:
        """Получить все автомобили (включая удаленные)."""
        db_vehicles = self.db.query(VehicleDB).all()
        return [Vehicle(**v.__dict__) for v in db_vehicles]

    def find_active_by_id(self, vehicle_id: int) -> Vehicle | None:
        db_vehicle = self.db.query(VehicleDB).filter(
            VehicleDB.id == vehicle_id, VehicleDB.is_active
        ).first()
        return Vehicle(**db_vehicle.__dict__) if db_vehicle else None

    def update_km(self, vehicle_id: int, new_km: int) -> Vehicle | None:
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            db_vehicle.current_km = new_km
            self.db.commit()
            self.db.refresh(db_vehicle)
            return Vehicle(**db_vehicle.__dict__)
        return None

    def delete(self, vehicle_id: int) -> bool:
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            db_vehicle.is_active = False
            self.db.commit()
            return True
        return False

    def hard_delete(self, vehicle_id: int) -> bool:
        """Полностью удалить автомобиль из БД."""
        db_vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if db_vehicle:
            self.db.delete(db_vehicle)
            self.db.commit()
            return True
        return False
