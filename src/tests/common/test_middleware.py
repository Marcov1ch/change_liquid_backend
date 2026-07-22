import logging
from unittest.mock import MagicMock, patch
from datetime import date

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.common.enums import ComponentType
from app.common.middleware import (
    LoggingMiddleware,
    verify_vehicle_access,
    verify_replacement_access,
)
from app.services.dto import VehicleDTO, ReplacementDTO


@pytest.fixture
def vehicle_dto() -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='Toyota', model='Camry', brand_id=1, model_id=1,
        plate_number='A123AA178', year=2020, current_km=50000,
        is_active=True, owner_id=42,
        intervals={'engine_oil': 7000},
        notify_flags={'engine_oil': True},
    )


@pytest.fixture
def replacement_dto(vehicle_dto: VehicleDTO) -> ReplacementDTO:
    return ReplacementDTO(
        id=1, vehicle_id=vehicle_dto.id,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1 5W-30',
        component_price=3000, work_price=1000,
        replacement_date=date(2024, 6, 1),
        km_at_replacement=40000, interval_km=7000,
    )


class TestVerifyVehicleAccess:

    def test_returns_vehicle_when_owner_matches(
        self, vehicle_dto: VehicleDTO,
    ) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 42

        with patch('app.common.middleware.VehicleService') as mock_service:
            mock_service.return_value.get_by_id.return_value = vehicle_dto

            result = verify_vehicle_access(
                vehicle_id=1, db=db, current_user=current_user,
            )

        assert result is vehicle_dto
        assert result.id == 1
        assert result.owner_id == 42
        mock_service.return_value.get_by_id.assert_called_once_with(1)

    def test_raises_404_when_vehicle_not_found(self) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 42

        with patch('app.common.middleware.VehicleService') as mock_service:
            mock_service.return_value.get_by_id.return_value = None

            with pytest.raises(HTTPException) as exc:
                verify_vehicle_access(
                    vehicle_id=999, db=db, current_user=current_user,
                )

        assert exc.value.status_code == 404
        assert 'not found' in exc.value.detail.lower()

    def test_raises_403_when_owner_does_not_match(
        self, vehicle_dto: VehicleDTO,
    ) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 99  # владелец — 42

        with patch('app.common.middleware.VehicleService') as mock_service:
            mock_service.return_value.get_by_id.return_value = vehicle_dto

            with pytest.raises(HTTPException) as exc:
                verify_vehicle_access(
                    vehicle_id=1, db=db, current_user=current_user,
                )

        assert exc.value.status_code == 403
        assert 'denied' in exc.value.detail.lower()


class TestVerifyReplacementAccess:

    def test_returns_replacement_when_owner_matches(
        self, replacement_dto: ReplacementDTO, vehicle_dto: VehicleDTO,
    ) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 42

        with (
            patch('app.common.middleware.ReplacementService') as mock_rep_service,
            patch('app.common.middleware.VehicleService') as mock_veh_service,
        ):
            mock_rep_service.return_value.get_by_id.return_value = replacement_dto
            mock_veh_service.return_value.get_by_id.return_value = vehicle_dto

            result = verify_replacement_access(
                replacement_id=1, db=db, current_user=current_user,
            )

        assert result is replacement_dto
        assert result.id == 1
        mock_rep_service.return_value.get_by_id.assert_called_once_with(1)
        mock_veh_service.return_value.get_by_id.assert_called_once_with(vehicle_dto.id)

    def test_raises_404_when_replacement_not_found(self) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 42

        with patch('app.common.middleware.ReplacementService') as mock_rep_service:
            mock_rep_service.return_value.get_by_id.return_value = None

            with pytest.raises(HTTPException) as exc:
                verify_replacement_access(
                    replacement_id=999, db=db, current_user=current_user,
                )

        assert exc.value.status_code == 404
        assert 'replacement' in exc.value.detail.lower()

    def test_raises_403_when_vehicle_owner_does_not_match(
        self, replacement_dto: ReplacementDTO, vehicle_dto: VehicleDTO,
    ) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 99  # не владелец

        with (
            patch('app.common.middleware.ReplacementService') as mock_rep_service,
            patch('app.common.middleware.VehicleService') as mock_veh_service,
        ):
            mock_rep_service.return_value.get_by_id.return_value = replacement_dto
            mock_veh_service.return_value.get_by_id.return_value = vehicle_dto

            with pytest.raises(HTTPException) as exc:
                verify_replacement_access(
                    replacement_id=1, db=db, current_user=current_user,
                )

        assert exc.value.status_code == 403
        assert 'denied' in exc.value.detail.lower()

    def test_raises_403_when_vehicle_not_found(
        self, replacement_dto: ReplacementDTO,
    ) -> None:
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 42

        with (
            patch('app.common.middleware.ReplacementService') as mock_rep_service,
            patch('app.common.middleware.VehicleService') as mock_veh_service,
        ):
            mock_rep_service.return_value.get_by_id.return_value = replacement_dto
            mock_veh_service.return_value.get_by_id.return_value = None

            with pytest.raises(HTTPException) as exc:
                verify_replacement_access(
                    replacement_id=1, db=db, current_user=current_user,
                )

        assert exc.value.status_code == 403
        assert 'denied' in exc.value.detail.lower()


class TestLoggingMiddleware:

    def test_logs_request_and_status(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO)

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get('/test')
        async def test_route() -> dict[str, str]:
            return {'ok': 'true'}

        with TestClient(app) as client:
            response = client.get('/test')

        assert response.status_code == 200
        assert response.json() == {'ok': 'true'}
        assert len(caplog.records) >= 1
        log = caplog.records[0]
        assert log.levelname == 'INFO'
        assert 'GET' in log.getMessage()
        assert '/test' in log.getMessage()
        assert '200' in log.getMessage()

    def test_logs_4xx_status(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO)

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get('/not-found')
        async def not_found() -> None:
            raise HTTPException(status_code=404, detail='Not found')

        with TestClient(app) as client:
            response = client.get('/not-found')

        assert response.status_code == 404
        assert len(caplog.records) >= 1
        log = caplog.records[0]
        assert '404' in log.getMessage()
