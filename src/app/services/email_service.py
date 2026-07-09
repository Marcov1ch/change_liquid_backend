import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_reset_password_email(to_email: str, token: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.mail.ru")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    reset_link = f"{frontend_url}/reset-password?token={token}"

    subject = "Восстановление пароля — Car Liquid Tracker"
    body = f"""
    <h2>Восстановление пароля</h2>
    <p>Вы запросили восстановление пароля. Перейдите по ссылке ниже, чтобы задать новый пароль:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>Ссылка действительна в течение 15 минут.</p>
    <p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
