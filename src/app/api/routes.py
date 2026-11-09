from fastapi import FastAPI, APIRouter

from app.api.enums.routes import router as enums_router
from app.api.fuel_record.routes import router as fuel_record_router
from app.api.other_expense.routes import router as other_expense_router
from app.api.repair.routes import router as repair_router
from app.api.replacement.routes import router as replacement_router
from app.api.share.routes import router as share_router
from app.api.tire_set.routes import router as tire_set_router
from app.api.vehicle.routes import router as vehicle_router


def setup_routes(app: FastAPI) -> None:
    """Инициализирует маршруты приложения."""
    router = APIRouter(prefix="/api/v1")

    router.include_router(vehicle_router)
    router.include_router(replacement_router)
    router.include_router(tire_set_router)
    router.include_router(fuel_record_router)
    router.include_router(other_expense_router)
    router.include_router(repair_router)
    router.include_router(share_router)
    router.include_router(enums_router)

    app.include_router(router)
