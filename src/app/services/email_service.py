import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from app.common.utils.templates.email import (
    render_reset_password_body,
    render_replacement_notification_body,
)


def _get_smtp_config() -> dict:
    """Получить SMTP конфигурацию из env."""
    return {
        "host": os.getenv("SMTP_HOST", "smtp.mail.ru"),
        "port": int(os.getenv("SMTP_PORT", "465")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:5173"),
    }


def _send_email(to_email: str, subject: str, body: str) -> None:
    """Отправить HTML-письмо через SMTP."""
    config = _get_smtp_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["from_addr"]
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config["host"], config["port"], context=context) as server:
        server.login(config["user"], config["password"])
        server.sendmail(config["from_addr"], to_email, msg.as_string())


def send_replacement_notification_email(
    to_email: str,
    vehicle_info: str,
    plate_number: str,
    current_km: int,
    due_items: list[dict],
) -> None:
    """Отправить уведомление о необходимости замены жидкостей."""
    config = _get_smtp_config()
    subject = "⚠️ Car Liquid Tracker — требуется замена жидкостей"
    body = render_replacement_notification_body(
        frontend_url=config['frontend_url'],
        vehicle_info=vehicle_info,
        plate_number=plate_number,
        current_km=current_km,
        due_items=due_items,
    )
    _send_email(to_email, subject, body)


def send_reset_password_email(to_email: str, token: str) -> None:
    """Отправить письмо для восстановления пароля."""
    config = _get_smtp_config()
    reset_link = f"{config['frontend_url']}/reset-password?token={token}"

    subject = "Восстановление пароля — Car Liquid Tracker"
    body = render_reset_password_body(reset_link)
    _send_email(to_email, subject, body)
