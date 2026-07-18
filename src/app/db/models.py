from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


class BrandDB(Base):  # type: ignore
    """Марка автомобиля."""

    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    models = relationship("ModelDB", back_populates="brand")


class ModelDB(Base):  # type: ignore
    """Модель автомобиля."""

    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    name = Column(String, nullable=False)

    brand = relationship("BrandDB", back_populates="models")


class UserDB(Base):  # type: ignore
    """Пользователь системы."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicles = relationship("VehicleDB", back_populates="owner")


class VehicleDB(Base):  # type: ignore
    """Автомобиль пользователя."""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    plate_number = Column(String, unique=True, nullable=False)
    year = Column(Integer, nullable=False)
    current_km = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # defaults управляются app.common.component_config COMPONENTS_CONFIG
    oil_interval_km = Column(Integer)
    transmission_interval_km = Column(Integer)
    brake_interval_km = Column(Integer)
    coolant_interval_km = Column(Integer)
    power_steering_interval_km = Column(Integer)
    differential_oil_interval_km = Column(Integer)

    oil_notify_enabled = Column(Boolean, default=True)
    transmission_notify_enabled = Column(Boolean, default=True)
    brake_notify_enabled = Column(Boolean, default=True)
    coolant_notify_enabled = Column(Boolean, default=True)
    power_steering_notify_enabled = Column(Boolean, default=True)
    differential_oil_notify_enabled = Column(Boolean, default=True)

    owner = relationship("UserDB", back_populates="vehicles")
    brand_ref = relationship("BrandDB", lazy="joined")
    model_ref = relationship("ModelDB", lazy="joined")

    replacements = relationship("ReplacementDB", back_populates="vehicle")


class ReplacementDB(Base):  # type: ignore
    """Замена компонента (запись о выполненной замене)."""

    __tablename__ = "replacements"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    component_type = Column(String, nullable=False)
    component_name = Column(String, nullable=False)
    component_price = Column(Integer, nullable=True)
    work_price = Column(Integer, nullable=True)
    replacement_date = Column(Date, nullable=False)
    km_at_replacement = Column(Integer, nullable=False)
    interval_km = Column(Integer, nullable=False)

    warning_notified = Column(Boolean, default=False)
    critical_notified = Column(Boolean, default=False)
    overdue_notified_at_km = Column(Integer, nullable=True)

    vehicle = relationship("VehicleDB", back_populates="replacements")
