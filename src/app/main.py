import uvicorn
from fastapi import FastAPI

from app.api.routes import setup_routes
from app.db.database import init_db


def create_app() -> FastAPI:
    """Создание приложения."""

    init_db()

    app = FastAPI(
        title='Change Liquid',
        version='1.0.0',
        description='Приложение для учета замены жидкостей',
        debug=False,
    )

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
