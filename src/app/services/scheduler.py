import logging
from datetime import date
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from app.common.constants import DATE_WARNING_DAYS
from app.common.component_config import COMPONENTS_CONFIG
from app.common.enums import ComponentType
from app.common.utils.interval_utils import add_months
from app.db.database import SessionLocal
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.email_service import send_date_notification_email

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _resolve_next_change_date(
    vehicle: dict[str, Any],
    last_repl: dict[str, Any],
) -> date | None:
    """Определить дату следующей замены из настроек авто (или сохранённую для шин)."""
    comp_key: str = last_repl["component_type"]
    if comp_key == ComponentType.TIRE_CHANGE.value:
        stored_date: date | None = last_repl.get("next_change_date")
        return stored_date

    months: int | None = vehicle.get("interval_months", {}).get(comp_key)
    replacement_date: date | None = last_repl.get("replacement_date")
    if months is None or replacement_date is None:
        return None
    next_date: date = add_months(replacement_date, months)
    return next_date


def _check_date_notifications() -> None:
    """Проверить date-based компоненты и отправить уведомления."""
    db = SessionLocal()
    try:
        vehicle_repo = VehicleRepository(db)
        replacement_repo = ReplacementRepository(db)

        vehicles = vehicle_repo.find_all_active_with_owner()

        # Пробегаемся по настраиваемым компонентам + шинам
        comp_keys = [cfg.type.value for cfg in COMPONENTS_CONFIG] + [ComponentType.TIRE_CHANGE.value]

        for vehicle in vehicles:
            notify_flags = vehicle["notify_flags"]

            for comp_key in comp_keys:
                if not notify_flags.get(comp_key, True):
                    continue

                last_repl = replacement_repo.get_last_replacement_with_notify(
                    vehicle["id"], ComponentType(comp_key)
                )
                if not last_repl:
                    continue

                next_change_date = _resolve_next_change_date(vehicle, last_repl)
                if not next_change_date:
                    continue

                today = date.today()
                days_remaining = (next_change_date - today).days
                component_name = last_repl["component_name"]

                if days_remaining <= 0:
                    if last_repl.get("date_overdue_notified"):
                        continue
                    is_overdue = True
                elif days_remaining <= DATE_WARNING_DAYS:
                    if last_repl.get("date_warning_notified"):
                        continue
                    is_overdue = False
                else:
                    if last_repl.get("date_warning_notified") or last_repl.get("date_overdue_notified"):
                        replacement_repo.update_date_notify_tracking(
                            last_repl["id"],
                            date_warning_notified=False,
                            date_overdue_notified=False,
                        )
                    continue

                try:
                    send_date_notification_email(
                        to_email=vehicle["owner_email"],
                        username=vehicle["owner_username"],
                        brand=vehicle["brand"],
                        model=vehicle["model"],
                        plate_number=vehicle["plate_number"],
                        component_name=component_name,
                        next_change_date=next_change_date.isoformat(),
                        days_remaining=days_remaining,
                        is_overdue=is_overdue,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send date %s email for vehicle %s, component %s",
                        "overdue" if is_overdue else "warning",
                        vehicle["id"], component_name,
                    )
                else:
                    replacement_repo.update_date_notify_tracking(
                        last_repl["id"],
                        date_warning_notified=not is_overdue,
                        date_overdue_notified=is_overdue,
                    )
                    logger.info(
                        "Date %s email sent for vehicle %s, component %s",
                        "overdue" if is_overdue else "warning",
                        vehicle["id"], component_name,
                    )
    except Exception:
        logger.exception("Error in _check_date_notifications")
    finally:
        db.close()


def start_scheduler() -> None:
    """Запустить фоновый планировщик."""
    if scheduler.running:
        return

    scheduler.add_job(
        _check_date_notifications,
        trigger="cron",
        hour=9,
        minute=0,
        id="check_date_notifications",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily check_date_notifications at 09:00")


def stop_scheduler() -> None:
    """Остановить планировщик."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
