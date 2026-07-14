from pydantic import BaseModel


class BrandResponse(BaseModel):
    """Модель марки для ответа."""
    value: str
    label: str


class BrandsResponse(BaseModel):
    """Список марок."""
    brands: list[BrandResponse]


class ModelResponse(BaseModel):
    """Модель модели для ответа."""
    value: str
    label: str


class ModelsResponse(BaseModel):
    """Список моделей."""
    models: list[ModelResponse]


class ComponentItemResponse(BaseModel):
    """Модель компонента для ответа."""
    value: str
    label: str


class ComponentsResponse(BaseModel):
    """Список компонентов."""
    components: list[ComponentItemResponse]


class ComponentConfigResponse(BaseModel):
    """Конфигурация одного компонента."""
    key: str
    name: str
    default_interval: int


class ComponentConfigsResponse(BaseModel):
    """Список конфигураций компонентов."""
    configs: list[ComponentConfigResponse]
