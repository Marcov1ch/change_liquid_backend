from fastapi import APIRouter

from app.api.share.handler import share_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/share",
    share_handler.get_share,
    methods=["GET"],
    tags=["share"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/share",
    share_handler.enable_share,
    methods=["POST"],
    tags=["share"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/share/rotate",
    share_handler.rotate_share,
    methods=["POST"],
    tags=["share"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/share",
    share_handler.disable_share,
    methods=["DELETE"],
    tags=["share"],
)
router.add_api_route(
    "/public/vehicles/{token}",
    share_handler.get_public_vehicle,
    methods=["GET"],
    tags=["public"],
)
