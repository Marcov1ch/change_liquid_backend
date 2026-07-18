from datetime import date

import pytest

from app.common.enums import ComponentType, StatusEnum
from app.common.utils.calculator import StatusCalculator
from app.services.dto import VehicleDTO, ReplacementDTO


@pytest.fixture
def vehicle() -> VehicleDTO:
    return VehicleDTO(
        id=1,
        brand='Toyota',
        model='Camry',
        brand_id=1,
        model_id=1,
        plate_number='A123AA178',
        year=2020,
        current_km=13000,
        is_active=True,
        owner_id=1,
        intervals={'engine_oil': 7000, 'brake_fluid': 7000},
        notify_flags={'engine_oil': True, 'brake_fluid': True},
    )


@pytest.fixture
def replacement_good() -> ReplacementDTO:
    return ReplacementDTO(
        id=1,
        vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=5000,
        work_price=1000,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000,
        interval_km=7000,
    )


@pytest.fixture
def replacement_overdue() -> ReplacementDTO:
    return ReplacementDTO(
        id=2,
        vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=5000,
        work_price=1000,
        replacement_date=date(2023, 1, 1),
        km_at_replacement=5000,
        interval_km=7000,
    )


@pytest.fixture
def replacement_brake_overdue() -> ReplacementDTO:
    return ReplacementDTO(
        id=3,
        vehicle_id=1,
        component_type=ComponentType.BRAKE_FLUID,
        component_name='Dot 4',
        component_price=2000,
        work_price=500,
        replacement_date=date(2023, 6, 1),
        km_at_replacement=5000,
        interval_km=7000,
    )


class TestGetVehicleStatus:

    def test_no_replacements_returns_unknown(self, vehicle: VehicleDTO) -> None:
        assert StatusCalculator.get_vehicle_status(vehicle, []) == StatusEnum.UNKNOWN.value

    def test_single_good_replacement_returns_good(
        self,
        vehicle: VehicleDTO,
        replacement_good: ReplacementDTO,
    ) -> None:
        assert StatusCalculator.get_vehicle_status(vehicle, [replacement_good]) == StatusEnum.GOOD.value

    def test_single_overdue_replacement_returns_overdue(
        self,
        vehicle: VehicleDTO,
        replacement_overdue: ReplacementDTO,
    ) -> None:
        assert StatusCalculator.get_vehicle_status(vehicle, [replacement_overdue]) == StatusEnum.OVERDUE.value

    def test_two_replacements_same_type_different_km_uses_latest(
        self,
        vehicle: VehicleDTO,
        replacement_good: ReplacementDTO,
        replacement_overdue: ReplacementDTO,
    ) -> None:
        result = StatusCalculator.get_vehicle_status(vehicle, [replacement_overdue, replacement_good])
        assert result == StatusEnum.GOOD.value

    def test_two_replacements_same_km_newer_id_wins(
        self,
        vehicle: VehicleDTO,
    ) -> None:
        older = ReplacementDTO(
            id=1, vehicle_id=1,
            component_type=ComponentType.ENGINE_OIL,
            component_name='Old', component_price=0, work_price=0,
            replacement_date=date(2024, 1, 1),
            km_at_replacement=10000, interval_km=7000,
        )
        newer = ReplacementDTO(
            id=2, vehicle_id=1,
            component_type=ComponentType.ENGINE_OIL,
            component_name='New', component_price=0, work_price=0,
            replacement_date=date(2024, 6, 1),
            km_at_replacement=10000, interval_km=7000,
        )
        current = ReplacementDTO(
            id=3, vehicle_id=1,
            component_type=ComponentType.ENGINE_OIL,
            component_name='Current', component_price=0, work_price=0,
            replacement_date=date(2025, 1, 1),
            km_at_replacement=18000, interval_km=7000,
        )
        result = StatusCalculator.get_vehicle_status(vehicle, [newer, older, current])
        assert result == StatusEnum.GOOD.value

    def test_multiple_types_worst_status_wins(
        self,
        vehicle: VehicleDTO,
        replacement_good: ReplacementDTO,
        replacement_brake_overdue: ReplacementDTO,
    ) -> None:
        result = StatusCalculator.get_vehicle_status(
            vehicle, [replacement_good, replacement_brake_overdue],
        )
        assert result == StatusEnum.OVERDUE.value

    def test_type_without_interval_skipped_and_does_not_affect_result(
        self,
        vehicle: VehicleDTO,
        replacement_good: ReplacementDTO,
    ) -> None:
        no_interval = ReplacementDTO(
            id=3, vehicle_id=1,
            component_type=ComponentType.COOLANT,
            component_name='Antifreeze', component_price=0, work_price=0,
            replacement_date=date(2024, 1, 1),
            km_at_replacement=10000, interval_km=60000,
        )
        result = StatusCalculator.get_vehicle_status(vehicle, [replacement_good, no_interval])
        assert result == StatusEnum.GOOD.value

    def test_two_types_warning_and_good_returns_warning(self) -> None:
        v = VehicleDTO(
            id=1, brand='', model='', brand_id=1, model_id=1,
            plate_number='', year=2000, current_km=16000,
            is_active=True, owner_id=1,
            intervals={'engine_oil': 7000, 'brake_fluid': 40000},
            notify_flags={},
        )
        close = ReplacementDTO(
            id=1, vehicle_id=1,
            component_type=ComponentType.ENGINE_OIL,
            component_name='Oil', component_price=0, work_price=0,
            replacement_date=date(2024, 1, 1),
            km_at_replacement=10000, interval_km=7000,
        )
        fresh = ReplacementDTO(
            id=2, vehicle_id=1,
            component_type=ComponentType.BRAKE_FLUID,
            component_name='Brake', component_price=0, work_price=0,
            replacement_date=date(2024, 6, 1),
            km_at_replacement=5000, interval_km=40000,
        )
        result = StatusCalculator.get_vehicle_status(v, [close, fresh])
        assert result == StatusEnum.WARNING.value
