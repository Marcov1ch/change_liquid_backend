from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.enums.schema import (
    BrandsResponse,
    BrandResponse,
    ModelsResponse,
    ModelResponse,
    ComponentsResponse,
    ComponentItemResponse,
    ComponentConfigsResponse,
    ComponentConfigResponse,
)
from app.common.enums import ComponentType
from app.common.component_config import COMPONENTS_CONFIG
from app.db.database import get_db
from app.repository.enum_repository import EnumRepository


class EnumsHandler:
    async def get_brands(self, db: Session = Depends(get_db)) -> BrandsResponse:
        """Получить список марок автомобилей."""
        repo = EnumRepository(db)
        brands = repo.get_all_brands()
        return BrandsResponse(
            brands=[BrandResponse(value=b.name, label=b.name) for b in brands]
        )

    async def get_models(self, brand: str, db: Session = Depends(get_db)) -> ModelsResponse:
        """Получить список моделей для конкретной марки."""
        repo = EnumRepository(db)
        models = repo.get_models_by_brand(brand)
        if not models:
            models_list = [ModelResponse(value="Другая модель", label="Другая модель")]
        else:
            models_list = [ModelResponse(value=m.name, label=m.name) for m in models]
        return ModelsResponse(models=models_list)

    async def get_components(self) -> ComponentsResponse:
        """Получить список типов компонентов."""
        components = [
            ComponentItemResponse(value=component.value, label=component.value.replace('_', ' ').title())
            for component in ComponentType
        ]
        return ComponentsResponse(components=components)

    async def get_component_configs(self) -> ComponentConfigsResponse:
        """Получить конфигурации всех отслеживаемых компонентов."""
        configs = [
            ComponentConfigResponse(
                key=cfg.type.value,
                name=cfg.name,
                default_interval=5000,
            )
            for cfg in COMPONENTS_CONFIG
        ]
        return ComponentConfigsResponse(configs=configs)


enums_handler = EnumsHandler()
