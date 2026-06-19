from enum import Enum


class LiquidType(Enum):
    """Enum жидкостей."""
    ENGINE_OIL = 'engine_oil'
    TRANSMISSION_OIL = "transmission_oil"
    COOLANT = "coolant"
    BRAKE_FLUID = "brake_fluid"
    POWER_STEERING_FLUID = "power_steering_fluid"
    DIFFERENTIAL_OIL = "differential_oil"


class BrandCar(Enum):
    """Enum марки авто."""
    TOYOTA = "Toyota"
    HONDA = "Honda"
    BMW = "BMW"
    MERCEDES = "Mercedes"
    AUDI = "Audi"
    VOLKSWAGEN = "Volkswagen"
    FORD = "Ford"
    CHEVROLET = "Chevrolet"
    HYUNDAI = "Hyundai"
    KIA = "Kia"
    NISSAN = "Nissan"
    MAZDA = "Mazda"
    SUBARU = "Subaru"
    VOLVO = "Volvo"


class CarModel(Enum):
    """Модели автомобилей по маркам."""
    # Toyota
    CAMRY = ("Toyota", "Camry")
    COROLLA = ("Toyota", "Corolla")
    RAV4 = ("Toyota", "RAV4")
    LAND_CRUISER = ("Toyota", "Land Cruiser")
    HIGHLANDER = ("Toyota", "Highlander")
    PRIUS = ("Toyota", "Prius")

    # Honda
    CR_V = ("Honda", "CR-V")
    CIVIC = ("Honda", "Civic")
    ACCORD = ("Honda", "Accord")
    PILOT = ("Honda", "Pilot")
    HR_V = ("Honda", "HR-V")
    FIT = ("Honda", "Fit")

    # BMW
    X5 = ("BMW", "X5")
    X3 = ("BMW", "X3")
    SERIES_3 = ("BMW", "3 Series")
    SERIES_5 = ("BMW", "5 Series")
    SERIES_7 = ("BMW", "7 Series")
    X1 = ("BMW", "X1")

    # Mercedes
    C_CLASS = ("Mercedes", "C-Class")
    E_CLASS = ("Mercedes", "E-Class")
    S_CLASS = ("Mercedes", "S-Class")
    GLE = ("Mercedes", "GLE")
    GLC = ("Mercedes", "GLC")
    A_CLASS = ("Mercedes", "A-Class")

    # Audi
    A4 = ("Audi", "A4")
    A6 = ("Audi", "A6")
    Q5 = ("Audi", "Q5")
    Q7 = ("Audi", "Q7")
    A3 = ("Audi", "A3")
    Q3 = ("Audi", "Q3")

    # Volkswagen
    GOLF = ("Volkswagen", "Golf")
    PASSAT = ("Volkswagen", "Passat")
    TIGUAN = ("Volkswagen", "Tiguan")
    POLO = ("Volkswagen", "Polo")
    TOUAREG = ("Volkswagen", "Touareg")

    # Ford
    FOCUS = ("Ford", "Focus")
    MONDEO = ("Ford", "Mondeo")
    KUGA = ("Ford", "Kuga")
    FIESTA = ("Ford", "Fiesta")
    EXPLORER = ("Ford", "Explorer")

    # Chevrolet
    CHEVROLET = ("Chevrolet", "Cruze")
    MALIBU = ("Chevrolet", "Malibu")
    TRAVERSE = ("Chevrolet", "Traverse")
    EQUINOX = ("Chevrolet", "Equinox")
    SPARK = ("Chevrolet", "Spark")

    # Hyundai
    SONATA = ("Hyundai", "Sonata")
    ELANTRA = ("Hyundai", "Elantra")
    SANTA_FE = ("Hyundai", "Santa Fe")
    TUCSON = ("Hyundai", "Tucson")
    KONA = ("Hyundai", "Kona")

    # Kia
    OPTIMA = ("Kia", "Optima")
    SPORTAGE = ("Kia", "Sportage")
    SORENTO = ("Kia", "Sorento")
    RIO = ("Kia", "Rio")
    CEED = ("Kia", "Ceed")

    # Nissan
    X_TRAIL = ("Nissan", "X-Trail")
    QASHQAI = ("Nissan", "Qashqai")
    JUKE = ("Nissan", "Juke")
    TEANA = ("Nissan", "Teana")
    MURANO = ("Nissan", "Murano")

    # Mazda
    CX_5 = ("Mazda", "CX-5")
    CX_9 = ("Mazda", "CX-9")
    MAZDA3 = ("Mazda", "Mazda3")
    MAZDA6 = ("Mazda", "Mazda6")
    CX_30 = ("Mazda", "CX-30")

    # Subaru
    OUTBACK = ("Subaru", "Outback")
    FORESTER = ("Subaru", "Forester")
    IMPREZA = ("Subaru", "Impreza")
    LEGACY = ("Subaru", "Legacy")
    XV = ("Subaru", "XV")

    # Volvo
    XC60 = ("Volvo", "XC60")
    XC90 = ("Volvo", "XC90")
    S60 = ("Volvo", "S60")
    V90 = ("Volvo", "V90")
    XC40 = ("Volvo", "XC40")

    OTHER = ("Other", "Другая модель")

    @property
    def brand(self) -> str:
        """Получить марку автомобиля."""
        return self.value[0]

    @property
    def model_name(self) -> str:
        """Получить название модели."""
        return self.value[1]

    @classmethod
    def get_models_by_brand(cls, brand: str) -> list[str]:
        """Получить список моделей для конкретной марки."""
        return [model.model_name for model in cls if model.brand == brand]


class StatusEnum(Enum):
    """Статусы по заменам жидкостей."""
    OVERDUE = "overdue"
    CRITICAL = "critical"
    WARNING = "warning"
    GOOD = "good"
    UNKNOWN = "unknown"
