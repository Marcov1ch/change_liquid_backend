import logging
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routes import setup_routes
from app.db.database import init_db
from app.db.migrate import run_migrations
from app.auth.handler import router as auth_router
from app.common.middleware import LoggingMiddleware


def create_app() -> FastAPI:
    """Создание приложения ."""

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        stream=sys.stdout,
    )

    run_migrations()
    init_db()

    app = FastAPI(
        title='Change Liquid',
        version='1.0.0',
        description='Приложение для учета замены жидкостей',
        debug=False,
    )

    app.add_middleware(LoggingMiddleware)

    app.include_router(auth_router)

    setup_routes(app)

    return app


app = create_app()

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        reload=True,
    )
