from sqlalchemy.orm import Session

from app.db.models import BrandDB, ModelDB


class EnumRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_brands(self) -> list[BrandDB]:
        return self.db.query(BrandDB).order_by(BrandDB.id).all()  # type: ignore[no-any-return]

    def get_models_by_brand(self, brand_name: str) -> list[ModelDB]:
        return (  # type: ignore[no-any-return]
            self.db.query(ModelDB)
            .join(BrandDB)
            .filter(BrandDB.name == brand_name)
            .order_by(ModelDB.id)
            .all()
        )

    def get_brand_by_name(self, name: str) -> BrandDB | None:
        return self.db.query(BrandDB).filter(BrandDB.name == name).first()

    def create_brand(self, name: str) -> BrandDB:
        brand = BrandDB(name=name)
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def create_model(self, brand_id: int, name: str) -> ModelDB:
        model = ModelDB(brand_id=brand_id, name=name)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model
