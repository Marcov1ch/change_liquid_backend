from sqlalchemy.orm import Session

from app.db.models import BrandDB, ModelDB

BRANDS_MODELS: dict[str, list[str]] = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Highlander", "Prius"],
    "Honda": ["CR-V", "Civic", "Accord", "Pilot", "HR-V", "Fit"],
    "BMW": ["X5", "X3", "3 Series", "5 Series", "7 Series", "X1"],
    "Mercedes": ["C-Class", "E-Class", "S-Class", "GLE", "GLC", "A-Class"],
    "Audi": ["A4", "A6", "Q5", "Q7", "A3", "Q3"],
    "Volkswagen": ["Golf", "Passat", "Tiguan", "Polo", "Touareg"],
    "Ford": ["Focus", "Mondeo", "Kuga", "Fiesta", "Explorer"],
    "Chevrolet": ["Cruze", "Malibu", "Traverse", "Equinox", "Spark"],
    "Hyundai": ["Sonata", "Elantra", "Santa Fe", "Tucson", "Kona"],
    "Kia": ["Optima", "Sportage", "Sorento", "Rio", "Ceed"],
    "Nissan": ["X-Trail", "Qashqai", "Juke", "Teana", "Murano"],
    "Mazda": ["CX-5", "CX-9", "Mazda3", "Mazda6", "CX-30"],
    "Subaru": ["Outback", "Forester", "Impreza", "Legacy", "XV"],
    "Volvo": ["XC60", "XC90", "S60", "V90", "XC40"],
}


def seed_brands(db: Session) -> None:
    """Заполнить таблицы brands и models, если они пусты."""
    if db.query(BrandDB).first():
        return

    for brand_name, models in BRANDS_MODELS.items():
        brand = BrandDB(name=brand_name)
        db.add(brand)
        db.flush()
        for model_name in models:
            db.add(ModelDB(brand_id=brand.id, name=model_name))

    db.commit()
