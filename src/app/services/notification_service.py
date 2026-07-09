from sqlalchemy.orm import Session

from app.db.models import VehicleDB, ReplacementDB
from app.common.liquid_config import LIQUIDS_CONFIG
from app.common.enums import LiquidType
from app.services.email_service import send_replacement_notification_email

LIQUID_NOTIFY_FIELD: dict[LiquidType, str] = {
    LiquidType.ENGINE_OIL: 'oil_notify_enabled',
    LiquidType.TRANSMISSION_OIL: 'transmission_notify_enabled',
    LiquidType.BRAKE_FLUID: 'brake_notify_enabled',
    LiquidType.COOLANT: 'coolant_notify_enabled',
    LiquidType.POWER_STEERING_FLUID: 'power_steering_notify_enabled',
    LiquidType.DIFFERENTIAL_OIL: 'differential_oil_notify_enabled',
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def check_and_notify(self, vehicle_id: int) -> None:
        """Проверить замены и отправить уведомления, если нужно."""
        vehicle = self.db.query(VehicleDB).filter(VehicleDB.id == vehicle_id).first()
        if not vehicle or not vehicle.is_active:
            return

        owner = vehicle.owner
        if not owner or not owner.email:
            return

        due_items: list[dict] = []

        for config in LIQUIDS_CONFIG:
            notify_field = LIQUID_NOTIFY_FIELD.get(config.type)
            if notify_field is None:
                continue
            if not getattr(vehicle, notify_field, True):
                continue

            last_replacement = (
                self.db.query(ReplacementDB)
                .filter(
                    ReplacementDB.vehicle_id == vehicle_id,
                    ReplacementDB.liquid_type == config.type.value,
                )
                .order_by(ReplacementDB.km_at_replacement.desc())
                .first()
            )
            if not last_replacement:
                continue

            interval = getattr(vehicle, config.interval_field, last_replacement.interval_km)
            next_km = last_replacement.km_at_replacement + interval
            km_remaining = next_km - vehicle.current_km

            if km_remaining <= 0:
                if last_replacement.overdue_notified_at_km is None:
                    due_items.append({
                        'level': 'overdue',
                        'liquid_type': config.type.value,
                        'km_at_replacement': last_replacement.km_at_replacement,
                        'next_replacement_km': next_km,
                    })
                    last_replacement.overdue_notified_at_km = vehicle.current_km
                elif vehicle.current_km - last_replacement.overdue_notified_at_km >= 500:
                    due_items.append({
                        'level': 'overdue',
                        'liquid_type': config.type.value,
                        'km_at_replacement': last_replacement.km_at_replacement,
                        'next_replacement_km': next_km,
                    })
                    last_replacement.overdue_notified_at_km = vehicle.current_km

            elif km_remaining <= 500 and not last_replacement.critical_notified:
                due_items.append({
                    'level': 'critical',
                    'liquid_type': config.type.value,
                    'km_at_replacement': last_replacement.km_at_replacement,
                    'next_replacement_km': next_km,
                })
                last_replacement.critical_notified = True

        if due_items:
            vehicle_info = f"{vehicle.brand_ref.name} {vehicle.model_ref.name}"
            send_replacement_notification_email(
                to_email=owner.email,
                vehicle_info=vehicle_info,
                plate_number=vehicle.plate_number,
                current_km=vehicle.current_km,
                due_items=due_items,
            )
            self.db.commit()
