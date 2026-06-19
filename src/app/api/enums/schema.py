from pydantic import BaseModel


class BrandResponse(BaseModel):
    value: str
    label: str


class BrandsResponse(BaseModel):
    brands: list[BrandResponse]


class ModelResponse(BaseModel):
    value: str
    label: str


class ModelsResponse(BaseModel):
    models: list[ModelResponse]


class LiquidResponse(BaseModel):
    value: str
    label: str


class LiquidsResponse(BaseModel):
    liquids: list[LiquidResponse]
