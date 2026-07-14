import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.enums import StatusEnum
from app.common.liquid_config import LIQUIDS_CONFIG
from app.common.utils.calculator import LiquidCalculator
from app.repository.vehicle_repository import VehicleRepository
from app.repository.replacement_repository import ReplacementRepository
from app.services.email_service import (
    send_grouped_notification_email,
    LiquidNotificationItem,
)


logger = logging.getLogger(__name__)

RE_NOTIFY_KM = 500

LIQUID_NAMES: dict[str, str] = {cfg.type.value: cfg.name for cfg in LIQUIDS_CONFIG}
LIQUID_NAMES_GEN: dict[str, str] = {cfg.type.value: cfg.name_genitive for cfg in LIQUIDS_CONFIG}


@dataclass
class _PendingItem:
    last: dict
    liq_key: str
    km_remaining: int
    status: str
    warning_notified: bool | None = None
    critical_notified: bool | None = None
    overdue_notified_at_km: int | None = None


def _send_grouped(
    replacement_repo: ReplacementRepository,
    vehicle: dict,
    pending: list[_PendingItem],
) -> None:
    if not pending:
        return

    to_email = vehicle.get("owner_email")
    if not to_email:
        return

    items = [
        LiquidNotificationItem(
            liquid_name=LIQUID_NAMES[p.liq_key],
            liquid_name_genitive=LIQUID_NAMES_GEN[p.liq_key],
            km_remaining=p.km_remaining,
            status=p.status,
        )
        for p in pending
    ]

    try:
        send_grouped_notification_email(
            to_email=to_email,
            username=vehicle["owner_username"],
            brand=vehicle["brand"],
            model=vehicle["model"],
            plate_number=vehicle["plate_number"],
            items=items,
        )

        for p in pending:
            replacement_repo.update_notify_tracking(
                p.last["id"],
                warning_notified=p.warning_notified,
                critical_notified=p.critical_notified,
                overdue_notified_at_km=p.overdue_notified_at_km,
            )

        liquids = ", ".join(LIQUID_NAMES[p.liq_key] for p in pending)
        logger.info(
            "Notification sent: user=%s vehicle=%s liquids=%s",
            vehicle["owner_username"], vehicle["id"], liquids,
        )
    except Exception as exc:
        logger.error(
            "Failed to send notification: user=%s vehicle=%s error=%s",
            vehicle["owner_username"], vehicle["id"], exc,
        )


def _reset_flags(replacement_repo: ReplacementRepository, last: dict) -> None:
    if last["warning_notified"] or last["critical_notified"] or last["overdue_notified_at_km"] is not None:
        replacement_repo.update_notify_tracking(
            last["id"],
            warning_notified=False,
            critical_notified=False,
            overdue_notified_at_km=None,
        )


def _check_vehicle(
    replacement_repo: ReplacementRepository,
    vehicle: dict,
) -> None:
    vehicle_id = vehicle["id"]
    pending: list[_PendingItem] = []

    for cfg in LIQUIDS_CONFIG:
        liq_key = cfg.type.value
        notify_enabled = vehicle.get(cfg.notify_field, True)
        if not notify_enabled:
            continue

        last = replacement_repo.get_last_replacement_with_notify(vehicle_id, cfg.type)
        if not last:
            continue

        interval = vehicle.get(cfg.interval_field)
        if not interval:
            continue

        current_km = vehicle["current_km"]

        result = LiquidCalculator.calculate_status(
            last["km_at_replacement"],
            interval,
            current_km,
        )

        status = result["status"]
        km_remaining = result["km_remaining"]
        warning_flag = bool(last["warning_notified"])
        critical_flag = bool(last["critical_notified"])
        overdue_km = last["overdue_notified_at_km"]

        if status == StatusEnum.GOOD.value:
            _reset_flags(replacement_repo, last)

        elif status == StatusEnum.WARNING.value:
            if not warning_flag:
                pending.append(_PendingItem(
                    last=last, liq_key=liq_key,
                    km_remaining=km_remaining, status=status,
                    warning_notified=True,
                    critical_notified=False,
                    overdue_notified_at_km=None,
                ))

        elif status == StatusEnum.CRITICAL.value:
            if km_remaining > 0 and not warning_flag:
                pending.append(_PendingItem(
                    last=last, liq_key=liq_key,
                    km_remaining=km_remaining, status=status,
                    warning_notified=True,
                    critical_notified=False,
                    overdue_notified_at_km=None,
                ))
            elif km_remaining == 0 and not critical_flag:
                pending.append(_PendingItem(
                    last=last, liq_key=liq_key,
                    km_remaining=km_remaining, status=status,
                    warning_notified=False,
                    critical_notified=True,
                    overdue_notified_at_km=None,
                ))

        elif status == StatusEnum.OVERDUE.value:
            next_km = last["km_at_replacement"] + last["interval_km"]

            if overdue_km is None:
                threshold = next_km + RE_NOTIFY_KM
            else:
                threshold = overdue_km + RE_NOTIFY_KM

            if current_km >= threshold:
                pending.append(_PendingItem(
                    last=last, liq_key=liq_key,
                    km_remaining=km_remaining, status=status,
                    warning_notified=False,
                    critical_notified=False,
                    overdue_notified_at_km=current_km,
                ))

    _send_grouped(replacement_repo, vehicle, pending)


def check_vehicle_notifications(db: Session, vehicle_id: int) -> None:
    vehicle_repo = VehicleRepository(db)
    replacement_repo = ReplacementRepository(db)

    vehicles = vehicle_repo.find_all_active_with_owner()
    vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not vehicle:
        return

    _check_vehicle(replacement_repo, vehicle)
