from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    email_verified = Column(Boolean, nullable=False, default=False, server_default="0")
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, nullable=False, server_default="0", default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicles = relationship("VehicleDB", back_populates="owner")


class VehicleDB(Base):  # type: ignore
    """Автомобиль пользователя."""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    plate_number = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    current_km = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    share_token = Column(String, unique=True, nullable=True, index=True)

    # defaults управляются app.common.component_config COMPONENTS_CONFIG
    oil_interval_km = Column(Integer)
    transmission_interval_km = Column(Integer)
    brake_interval_km = Column(Integer)
    coolant_interval_km = Column(Integer)
    power_steering_interval_km = Column(Integer)
    differential_oil_interval_km = Column(Integer)
    cabin_filter_interval_km = Column(Integer)
    spark_plugs_interval_km = Column(Integer)
    air_filter_interval_km = Column(Integer)
    fuel_filter_interval_km = Column(Integer)

    oil_notify_enabled = Column(Boolean, default=True)
    transmission_notify_enabled = Column(Boolean, default=True)
    brake_notify_enabled = Column(Boolean, default=True)
    coolant_notify_enabled = Column(Boolean, default=True)
    power_steering_notify_enabled = Column(Boolean, default=True)
    differential_oil_notify_enabled = Column(Boolean, default=True)
    cabin_filter_notify_enabled = Column(Boolean, default=True)
    spark_plugs_notify_enabled = Column(Boolean, default=True)
    air_filter_notify_enabled = Column(Boolean, default=True)
    fuel_filter_notify_enabled = Column(Boolean, default=True)

    oil_interval_months = Column(Integer, nullable=True)
    transmission_interval_months = Column(Integer, nullable=True)
    brake_interval_months = Column(Integer, nullable=True)
    coolant_interval_months = Column(Integer, nullable=True)
    power_steering_interval_months = Column(Integer, nullable=True)
    differential_oil_interval_months = Column(Integer, nullable=True)
    cabin_filter_interval_months = Column(Integer, nullable=True)
    spark_plugs_interval_months = Column(Integer, nullable=True)
    air_filter_interval_months = Column(Integer, nullable=True)
    fuel_filter_interval_months = Column(Integer, nullable=True)

    tire_notify_enabled = Column(Boolean, default=True)
    insurance_notify_enabled = Column(Boolean, default=True)
    parking_monthly_notify_enabled = Column(Boolean, default=True)

    owner = relationship("UserDB", back_populates="vehicles")
    brand_ref = relationship("BrandDB", lazy="joined")
    model_ref = relationship("ModelDB", lazy="joined")

    replacements = relationship("ReplacementDB", back_populates="vehicle")
    sizes = relationship("VehicleSizeDB", backref="vehicle", cascade="all, delete-orphan")
    other_expenses = relationship(
        "OtherExpenseDB",
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )
    repairs = relationship(
        "RepairDB",
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )
    fuel_records = relationship(
        "FuelRecordDB",
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )
    tire_sets = relationship(
        "TireSetDB",
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )


class TireSetDB(Base):  # type: ignore
    """Комплект шин автомобиля."""

    __tablename__ = "tire_sets"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    season = Column(String, nullable=False, default="all_season")
    purchase_date = Column(Date, nullable=True)
    purchase_price = Column(Integer, nullable=True)
    accumulated_km = Column(Integer, nullable=False, default=0, server_default="0")
    installed_km = Column(Integer, nullable=True)
    installed_date = Column(Date, nullable=True)
    is_installed = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicle = relationship("VehicleDB", back_populates="tire_sets")


class VehicleSizeDB(Base):  # type: ignore
    """Позиция диска или шины автомобиля."""

    __tablename__ = "vehicle_sizes"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String, nullable=False)  # 'rim' | 'tire'

    # Disk fields
    diameter = Column(Integer, nullable=True)
    pcd = Column(String, nullable=True)
    et_from = Column(Integer, nullable=True)
    et_to = Column(Integer, nullable=True)
    width_from = Column(Float, nullable=True)
    width_to = Column(Float, nullable=True)

    # Tire fields
    size = Column(String, nullable=True)
    label = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    interval_months = Column(Integer, nullable=True)
    next_change_date = Column(Date, nullable=True)
    tire_set_id = Column(
        Integer,
        ForeignKey("tire_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tire_event_type = Column(String, nullable=True)

    warning_notified = Column(Boolean, default=False)
    critical_notified = Column(Boolean, default=False)
    overdue_notified_at_km = Column(Integer, nullable=True)

    date_warning_notified = Column(Boolean, default=False)
    date_overdue_notified = Column(Boolean, default=False)

    source_repair_id = Column(
        Integer,
        ForeignKey("repairs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    vehicle = relationship("VehicleDB", back_populates="replacements")


class OtherExpenseDB(Base):  # type: ignore
    """Прочая трата на автомобиль."""

    __tablename__ = "other_expenses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    expense_date = Column(Date, nullable=False, index=True)
    amount = Column(Integer, nullable=False)

    vehicle = relationship("VehicleDB", back_populates="other_expenses")


class RepairDB(Base):  # type: ignore
    """Ремонт или обслуживание автомобиля."""

    __tablename__ = "repairs"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repair_date = Column(Date, nullable=False, index=True)
    km_at_repair = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    work_cost = Column(Integer, nullable=False, default=0, server_default="0")
    parts_cost = Column(Integer, nullable=False, default=0, server_default="0")

    vehicle = relationship("VehicleDB", back_populates="repairs")
    components = relationship(
        "RepairComponentDB",
        back_populates="repair",
        cascade="all, delete-orphan",
    )


class RepairComponentDB(Base):  # type: ignore
    """Выбранный km-based компонент ремонта."""

    __tablename__ = "repair_components"
    __table_args__ = (
        UniqueConstraint("repair_id", "component_type", name="uq_repair_component"),
    )

    id = Column(Integer, primary_key=True, index=True)
    repair_id = Column(
        Integer,
        ForeignKey("repairs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_type = Column(String, nullable=False)

    repair = relationship("RepairDB", back_populates="components")


class FuelRecordDB(Base):  # type: ignore
    """Запись о заправке автомобиля."""

    __tablename__ = "fuel_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fuel_date = Column(Date, nullable=False, index=True)
    km_at_fuel = Column(Integer, nullable=False)
    liters = Column(Float, nullable=False)
    total_cost = Column(Integer, nullable=False)

    vehicle = relationship("VehicleDB", back_populates="fuel_records")
