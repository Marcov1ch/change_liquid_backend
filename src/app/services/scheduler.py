import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.common.enums import ComponentType
from app.db.database import SessionLocal
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.email_service import send_date_notification_email

logger = logging.getLogger(__name__)

DATE_WARNING_DAYS = 5

scheduler = BackgroundScheduler()


def _check_date_notifications() -> None:
    """Проверить date-based компоненты (шины) и отправить уведомления."""
    db = SessionLocal()
    try:
        vehicle_repo = VehicleRepository(db)
        replacement_repo = ReplacementRepository(db)

        vehicles = vehicle_repo.find_all_active_with_owner()

        for vehicle in vehicles:
            notify_flags = vehicle["notify_flags"]
            if not notify_flags.get("tire_change", True):
                continue

            last_repl = replacement_repo.get_last_replacement_with_notify(
                vehicle["id"], ComponentType.TIRE_CHANGE
            )
            if not last_repl:
                continue

            next_change_date = last_repl.get("next_change_date")
            if not next_change_date:
                continue

            today = date.today()
            days_remaining = (next_change_date - today).days

            if days_remaining <= 0 and not last_repl.get("date_overdue_notified"):
                replacement_repo.update_date_notify_tracking(
                    last_repl["id"],
                    date_overdue_notified=True,
                )
                send_date_notification_email(
                    to_email=vehicle["owner_email"],
                    username=vehicle["owner_username"],
                    brand=vehicle["brand"],
                    model=vehicle["model"],
                    plate_number=vehicle["plate_number"],
                    component_name=last_repl["component_name"],
                    next_change_date=next_change_date.isoformat(),
                    days_remaining=days_remaining,
                    is_overdue=True,
                )
                logger.info(
                    "Date overdue email sent for vehicle %s, component %s",
                    vehicle["id"], last_repl["component_name"],
                )
            elif 0 < days_remaining <= DATE_WARNING_DAYS and not last_repl.get("date_warning_notified"):
                replacement_repo.update_date_notify_tracking(
                    last_repl["id"],
                    date_warning_notified=True,
                )
                send_date_notification_email(
                    to_email=vehicle["owner_email"],
                    username=vehicle["owner_username"],
                    brand=vehicle["brand"],
                    model=vehicle["model"],
                    plate_number=vehicle["plate_number"],
                    component_name=last_repl["component_name"],
                    next_change_date=next_change_date.isoformat(),
                    days_remaining=days_remaining,
                    is_overdue=False,
                )
                logger.info(
                    "Date warning email sent for vehicle %s, component %s",
                    vehicle["id"], last_repl["component_name"],
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
