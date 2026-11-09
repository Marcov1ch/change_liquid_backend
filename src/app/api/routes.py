from fastapi import FastAPI, APIRouter

from app.api.vehicle.handler import vehicle_handler
from app.api.replacement.handler import replacement_handler
from app.api.fuel_record.handler import fuel_record_handler
from app.api.other_expense.handler import other_expense_handler
from app.api.repair.handler import repair_handler
from app.api.enums.handler import enums_handler
from app.api.share.handler import share_handler
from app.api.tire_set.handler import tire_set_handler


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
        "/vehicles/{vehicle_id}/sizes",
        vehicle_handler.update_sizes,
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

    # Маршруты для комплектов шин
    router.add_api_route(
        "/vehicles/{vehicle_id}/tire-sets",
        tire_set_handler.get_tire_sets,
        methods=["GET"],
        tags=["tire-sets"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/tire-sets",
        tire_set_handler.create_tire_set,
        methods=["POST"],
        tags=["tire-sets"]
    )
    router.add_api_route(
        "/tire-sets/{tire_set_id}",
        tire_set_handler.update_tire_set,
        methods=["PATCH"],
        tags=["tire-sets"]
    )
    router.add_api_route(
        "/tire-sets/{tire_set_id}",
        tire_set_handler.delete_tire_set,
        methods=["DELETE"],
        tags=["tire-sets"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/tire-sets/{tire_set_id}/install",
        tire_set_handler.install_tire_set,
        methods=["POST"],
        tags=["tire-sets"]
    )

    # Маршруты для заправок
    router.add_api_route(
        "/vehicles/{vehicle_id}/fuel-records",
        fuel_record_handler.get_vehicle_fuel_records,
        methods=["GET"],
        tags=["fuel-records"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/fuel-records",
        fuel_record_handler.create_fuel_record,
        methods=["POST"],
        tags=["fuel-records"]
    )
    router.add_api_route(
        "/fuel-records/{record_id}",
        fuel_record_handler.get_fuel_record,
        methods=["GET"],
        tags=["fuel-records"]
    )
    router.add_api_route(
        "/fuel-records/{record_id}",
        fuel_record_handler.update_fuel_record,
        methods=["PATCH"],
        tags=["fuel-records"]
    )
    router.add_api_route(
        "/fuel-records/{record_id}",
        fuel_record_handler.delete_fuel_record,
        methods=["DELETE"],
        tags=["fuel-records"]
    )

    # Маршруты для прочих трат
    router.add_api_route(
        "/vehicles/{vehicle_id}/other-expenses",
        other_expense_handler.get_vehicle_other_expenses,
        methods=["GET"],
        tags=["other-expenses"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/other-expenses",
        other_expense_handler.create_other_expense,
        methods=["POST"],
        tags=["other-expenses"]
    )
    router.add_api_route(
        "/other-expenses/{expense_id}",
        other_expense_handler.get_other_expense,
        methods=["GET"],
        tags=["other-expenses"]
    )
    router.add_api_route(
        "/other-expenses/{expense_id}",
        other_expense_handler.update_other_expense,
        methods=["PATCH"],
        tags=["other-expenses"]
    )
    router.add_api_route(
        "/other-expenses/{expense_id}",
        other_expense_handler.delete_other_expense,
        methods=["DELETE"],
        tags=["other-expenses"]
    )

    # Маршруты для ремонтов
    router.add_api_route(
        "/vehicles/{vehicle_id}/repairs",
        repair_handler.get_vehicle_repairs,
        methods=["GET"],
        tags=["repairs"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/repairs",
        repair_handler.create_repair,
        methods=["POST"],
        tags=["repairs"]
    )
    router.add_api_route(
        "/repairs/{repair_id}",
        repair_handler.get_repair,
        methods=["GET"],
        tags=["repairs"]
    )
    router.add_api_route(
        "/repairs/{repair_id}",
        repair_handler.update_repair,
        methods=["PUT"],
        tags=["repairs"]
    )
    router.add_api_route(
        "/repairs/{repair_id}",
        repair_handler.delete_repair,
        methods=["DELETE"],
        tags=["repairs"]
    )

    # Маршруты для публичного шаринга
    router.add_api_route(
        "/vehicles/{vehicle_id}/share",
        share_handler.get_share,
        methods=["GET"],
        tags=["share"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/share",
        share_handler.enable_share,
        methods=["POST"],
        tags=["share"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/share/rotate",
        share_handler.rotate_share,
        methods=["POST"],
        tags=["share"]
    )
    router.add_api_route(
        "/vehicles/{vehicle_id}/share",
        share_handler.disable_share,
        methods=["DELETE"],
        tags=["share"]
    )
    router.add_api_route(
        "/public/vehicles/{token}",
        share_handler.get_public_vehicle,
        methods=["GET"],
        tags=["public"]
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
