from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import get_cors_origins


def setup_cors(app: FastAPI) -> None:
    """Настроить CORS для web- и Capacitor-клиентов."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'Accept'],
        expose_headers=['Retry-After'],
    )
