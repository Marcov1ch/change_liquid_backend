from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.enums.schema import (
    BrandsResponse,
    BrandResponse,
    ModelsResponse,
    ModelResponse,
    LiquidsResponse,
    LiquidResponse,
)
from app.common.enums import LiquidType
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

    async def get_liquids(self) -> LiquidsResponse:
        """Получить список типов жидкостей."""
        liquids = [
            LiquidResponse(value=liquid.value, label=liquid.value.replace('_', ' ').title())
            for liquid in LiquidType
        ]
        return LiquidsResponse(liquids=liquids)


enums_handler = EnumsHandler()
