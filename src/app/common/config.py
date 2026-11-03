import os


def get_frontend_url() -> str:
    """Базовый URL фронтенда."""
    return os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')


def build_share_url(token: str) -> str:
    """Публичная ссылка на профиль авто."""
    return f'{get_frontend_url()}/share/{token}'


def build_register_url() -> str:
    """Ссылка на регистрацию."""
    return f'{get_frontend_url()}/register'
