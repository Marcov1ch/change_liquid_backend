import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dataclasses import dataclass
from html import escape


@dataclass
class ComponentNotificationItem:
    component_name: str
    component_name_genitive: str
    km_remaining: int
    status: str


STATUS_ORDER = {"overdue": 3, "critical": 2, "warning": 1}
STATUS_HEADERS = {
    "overdue": ("🔴", "Просрочено! Требуется немедленная замена!"),
    "critical": ("🔴", "Требуется замена!"),
    "warning": ("🟡", "Пора заменить"),
}


def _html(value: object) -> str:
    """Экранировать значение для безопасной вставки в HTML-тело письма."""
    return escape(str(value), quote=True)


def _header(value: object) -> str:
    """Санитизировать значение для заголовка письма (убрать CR/LF)."""
    return str(value).replace('\r', ' ').replace('\n', ' ')


def _get_smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.mail.ru"),
        "port": int(os.getenv("SMTP_PORT", "465")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
    }


def _send_email(to_email: str, subject: str, body: str) -> None:
    cfg = _get_smtp_config()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
        server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["from"], to_email, msg.as_string())


def send_reset_password_email(to_email: str, token: str) -> None:
    """Отправить письмо для сброса пароля."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    subject = "Восстановление пароля — Change Liquid"
    body = f"""
    <h2>Восстановление пароля</h2>
    <p>Вы запросили восстановление пароля. Перейдите по ссылке ниже, чтобы задать новый пароль:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>Ссылка действительна в течение 15 минут.</p>
    <p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>
    """

    _send_email(to_email, subject, body)


def send_date_notification_email(
    to_email: str,
    username: str,
    brand: str,
    model: str,
    plate_number: str,
    component_name: str,
    next_change_date: str,
    days_remaining: int,
    is_overdue: bool = False,
) -> None:
    """Отправить email о date-based замене (шины)."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    if is_overdue:
        emoji = "🔴"
        status_text = "Просрочено! Требуется замена!"
    else:
        emoji = "🟡"
        status_text = "Скоро требуется замена"

    days_str = f"просрочено на {-days_remaining} дн." if is_overdue else f"осталось {days_remaining} дн."

    subject = _header(f"Change Liquid — {component_name}: требуется замена")

    body = f"""
    <h2>{emoji} {status_text}</h2>
    <p>Здравствуйте, <strong>{_html(username)}</strong>!</p>
    <p>По данным системы, на автомобиле
    <strong>{_html(brand)} {_html(model)}</strong> ({_html(plate_number)})<br>
    {_html(component_name)}: {days_str}</p>
    <p><strong>Дата следующей замены:</strong> {next_change_date}</p>
    <hr>
    <p style="font-size: 12px; color: #888;">
        Если вы не хотите получать уведомления,
        отключите их в настройках автомобиля:
        <br>
        <a href="{frontend_url}/">Перейти в настройки</a>
    </p>
    """

    _send_email(to_email, subject, body)


def _pick_worst_status(items: list[ComponentNotificationItem]) -> str:
    return max(items, key=lambda x: STATUS_ORDER.get(x.status, 0)).status


def _format_km(km: int) -> str:
    if km < 0:
        return f"просрочено на {-km} км"
    return f"осталось {km} км"


def send_grouped_notification_email(
    to_email: str,
    username: str,
    brand: str,
    model: str,
    plate_number: str,
    items: list[ComponentNotificationItem],
) -> None:
    """Отправить email с группировкой всех компонентов, требующих замены."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    worst = _pick_worst_status(items)
    emoji, header_text = STATUS_HEADERS.get(worst, ("🟡", "Пора заменить"))

    comp_items = "".join(
        f"<li><strong>{_html(item.component_name_genitive)}</strong> — {_format_km(item.km_remaining)}</li>"
        for item in items
    )

    first = items[0].component_name
    label = first if len(items) == 1 else f"{len(items)} компонентов"
    subject = _header(f"Change Liquid — {label}: требуется замена")

    body = f"""
    <h2>{emoji} {header_text}</h2>
    <p>Здравствуйте, <strong>{_html(username)}</strong>!</p>
    <p>По данным системы, на автомобиле
    <strong>{_html(brand)} {_html(model)}</strong> ({_html(plate_number)})<br>
    требуется замена:</p>
    <ul>{comp_items}</ul>
    <hr>
    <p style="font-size: 12px; color: #888;">
        Если вы не хотите получать уведомления,
        отключите их в настройках автомобиля:
        <br>
        <a href="{frontend_url}/">Перейти в настройки</a>
    </p>
    """

    _send_email(to_email, subject, body)
