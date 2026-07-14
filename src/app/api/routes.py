from fastapi import FastAPI, APIRouter

from app.api.vehicle.handler import vehicle_handler
from app.api.replacement.handler import replacement_handler
from app.api.enums.handler import enums_handler


def setup_routes(app: FastAPI) -> None:
    """Инициализирует маршруты приложения."""
    router = APIRouter(prefix="/api/v1")

    # Маршруты для автомобилей
    router.add_api_route(
        "/vehicles",
        vehicle_handler.get_vehicles,
        methods=["GET"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}",
        vehicle_handler.get_vehicle,
        methods=["GET"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles",
        vehicle_handler.create_vehicle,
        methods=["POST"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/km",
        vehicle_handler.update_vehicle_km,
        methods=["PATCH"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}",
        vehicle_handler.update_vehicle,
        methods=["PATCH"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/restore",
        vehicle_handler.restore_vehicle,
        methods=["PATCH"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/notify",
        vehicle_handler.update_notify,
        methods=["PATCH"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/intervals",
        vehicle_handler.update_vehicle_intervals,
        methods=["PATCH"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}",
        vehicle_handler.delete_vehicle,
        methods=["DELETE"],
        tags=["vehicles"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/hard",
        vehicle_handler.hard_delete_vehicle,
        methods=["DELETE"],
        tags=["vehicles"]
    )

    # Маршруты для замен жидкостей
    router.add_api_route(
        "/vehicles/{vehicle_id}/replacements",
        replacement_handler.get_vehicle_replacements,
        methods=["GET"],
        tags=["replacements"]
    )
    router.add_api_route(
        "/replacements/{replacement_id}",
        replacement_handler.get_replacement,
        methods=["GET"],
        tags=["replacements"]
    )
    router.add_api_route(
        "/replacements/{replacement_id}",
        replacement_handler.update_replacement,
        methods=["PUT"],
        tags=["replacements"]
    )
    router.add_api_route(
        "/replacements/{replacement_id}",
        replacement_handler.delete_replacement,
        methods=["DELETE"],
        tags=["replacements"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/replacements/bulk",
        replacement_handler.create_replacements,
        methods=["POST"],
        tags=["replacements"]
    )

    # Маршруты для получения enum
    router.add_api_route(
        "/enums/brands",
        enums_handler.get_brands,
        methods=["GET"],
        tags=["enums"]
    )
    router.add_api_route(
        "/enums/models/{brand}",
        enums_handler.get_models,
        methods=["GET"],
        tags=["enums"]
    )
    router.add_api_route(
        "/enums/components",
        enums_handler.get_components,
        methods=["GET"],
        tags=["enums"]
    )
    router.add_api_route(
        "/enums/component-configs",
        enums_handler.get_component_configs,
        methods=["GET"],
        tags=["enums"]
    )

    app.include_router(router)
