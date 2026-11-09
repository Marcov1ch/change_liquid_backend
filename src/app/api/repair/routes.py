from fastapi import APIRouter

from app.api.repair.handler import repair_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/repairs",
    repair_handler.get_vehicle_repairs,
    methods=["GET"],
    tags=["repairs"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/repairs",
    repair_handler.create_repair,
    methods=["POST"],
    tags=["repairs"],
)
router.add_api_route(
    "/repairs/{repair_id}",
    repair_handler.get_repair,
    methods=["GET"],
    tags=["repairs"],
)
router.add_api_route(
    "/repairs/{repair_id}",
    repair_handler.update_repair,
    methods=["PUT"],
    tags=["repairs"],
)
router.add_api_route(
    "/repairs/{repair_id}",
    repair_handler.delete_repair,
    methods=["DELETE"],
    tags=["repairs"],
)
