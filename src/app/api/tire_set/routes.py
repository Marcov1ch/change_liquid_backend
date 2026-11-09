from fastapi import APIRouter

from app.api.tire_set.handler import tire_set_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/tire-sets",
    tire_set_handler.get_tire_sets,
    methods=["GET"],
    tags=["tire-sets"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/tire-sets",
    tire_set_handler.create_tire_set,
    methods=["POST"],
    tags=["tire-sets"],
)
router.add_api_route(
    "/tire-sets/{tire_set_id}",
    tire_set_handler.update_tire_set,
    methods=["PATCH"],
    tags=["tire-sets"],
)
router.add_api_route(
    "/tire-sets/{tire_set_id}",
    tire_set_handler.delete_tire_set,
    methods=["DELETE"],
    tags=["tire-sets"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/tire-sets/{tire_set_id}/install",
    tire_set_handler.install_tire_set,
    methods=["POST"],
    tags=["tire-sets"],
)
