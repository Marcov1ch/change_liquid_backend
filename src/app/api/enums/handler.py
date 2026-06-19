from app.api.enums.schema import (
    BrandsResponse,
    BrandResponse,
    ModelsResponse,
    ModelResponse,
    LiquidsResponse,
    LiquidResponse,
)
from app.common.enums import (
    BrandCar,
    LiquidType,
    CarModel,
)


class EnumsHandler:
    async def get_brands(self) -> BrandsResponse:
        """Получить список марок автомобилей."""
        brands = [BrandResponse(value=brand.value, label=brand.value) for brand in BrandCar]
        return BrandsResponse(brands=brands)

    async def get_models(self, brand: str) -> ModelsResponse:
        """Получить список моделей для конкретной марки."""
        models = CarModel.get_models_by_brand(brand)
        if not models:
            models = ["Другая модель"]
        models_list = [ModelResponse(value=model, label=model) for model in models]
        return ModelsResponse(models=models_list)

    async def get_liquids(self) -> LiquidsResponse:
        """Получить список типов жидкостей."""
        liquids = [
            LiquidResponse(value=liquid.value, label=liquid.value.replace('_', ' ').title())
            for liquid in LiquidType
        ]
        return LiquidsResponse(liquids=liquids)


enums_handler = EnumsHandler()
