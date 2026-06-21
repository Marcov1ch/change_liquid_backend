from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


class UserDB(Base):  # type: ignore
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicles = relationship("VehicleDB", back_populates="owner")


class VehicleDB(Base):  # type: ignore
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)  # Enum -> String
    model = Column(String, nullable=False)
    plate_number = Column(String, unique=True, nullable=False)
    year = Column(Integer, nullable=False)
    current_km = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    oil_interval_km = Column(Integer, default=7000)
    transmission_interval_km = Column(Integer, default=60000)
    brake_interval_km = Column(Integer, default=40000)
    coolant_interval_km = Column(Integer, default=60000)
    power_steering_interval_km = Column(Integer, default=60000)
    differential_oil_interval_km = Column(Integer, default=60000)
    owner = relationship("UserDB", back_populates="vehicles")

    replacements = relationship("ReplacementDB", back_populates="vehicle")


class ReplacementDB(Base):  # type: ignore
    __tablename__ = "replacements"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    liquid_type = Column(String, nullable=False)
    liquid_name = Column(String, nullable=False)
    liquid_price = Column(Integer, nullable=True)
    work_price = Column(Integer, nullable=True)
    replacement_date = Column(Date, nullable=False)
    km_at_replacement = Column(Integer, nullable=False)
    interval_km = Column(Integer, nullable=False)

    vehicle = relationship("VehicleDB", back_populates="replacements")
