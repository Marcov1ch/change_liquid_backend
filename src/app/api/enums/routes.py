from fastapi import APIRouter

from app.api.enums.handler import enums_handler

router = APIRouter()

router.add_api_route(
    "/enums/brands",
    enums_handler.get_brands,
    methods=["GET"],
    tags=["enums"],
)
router.add_api_route(
    "/enums/models/{brand}",
    enums_handler.get_models,
    methods=["GET"],
    tags=["enums"],
)
router.add_api_route(
    "/enums/components",
    enums_handler.get_components,
    methods=["GET"],
    tags=["enums"],
)
router.add_api_route(
    "/enums/component-configs",
    enums_handler.get_component_configs,
    methods=["GET"],
    tags=["enums"],
)
