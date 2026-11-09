from fastapi import APIRouter

from app.api.replacement.handler import replacement_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/replacements",
    replacement_handler.get_vehicle_replacements,
    methods=["GET"],
    tags=["replacements"],
)
router.add_api_route(
    "/replacements/{replacement_id}",
    replacement_handler.get_replacement,
    methods=["GET"],
    tags=["replacements"],
)
router.add_api_route(
    "/replacements/{replacement_id}",
    replacement_handler.update_replacement,
    methods=["PUT"],
    tags=["replacements"],
)
router.add_api_route(
    "/replacements/{replacement_id}",
    replacement_handler.delete_replacement,
    methods=["DELETE"],
    tags=["replacements"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/replacements/bulk",
    replacement_handler.create_replacements,
    methods=["POST"],
    tags=["replacements"],
)
