from fastapi import APIRouter

from app.api.fuel_record.handler import fuel_record_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/fuel-records",
    fuel_record_handler.get_vehicle_fuel_records,
    methods=["GET"],
    tags=["fuel-records"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/fuel-records",
    fuel_record_handler.create_fuel_record,
    methods=["POST"],
    tags=["fuel-records"],
)
router.add_api_route(
    "/fuel-records/{record_id}",
    fuel_record_handler.get_fuel_record,
    methods=["GET"],
    tags=["fuel-records"],
)
router.add_api_route(
    "/fuel-records/{record_id}",
    fuel_record_handler.update_fuel_record,
    methods=["PATCH"],
    tags=["fuel-records"],
)
router.add_api_route(
    "/fuel-records/{record_id}",
    fuel_record_handler.delete_fuel_record,
    methods=["DELETE"],
    tags=["fuel-records"],
)
