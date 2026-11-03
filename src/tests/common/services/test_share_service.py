from unittest.mock import MagicMock

from app.services.dto import VehicleDTO
from app.services.share_service import VehicleShareService


def _vehicle(share_token: str | None = None) -> VehicleDTO:
    return VehicleDTO(
        id=1,
        brand='VW',
        model='Golf',
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2015,
        current_km=20000,
        is_active=True,
        owner_id=1,
        share_token=share_token,
    )


def _service() -> VehicleShareService:
    service = VehicleShareService.__new__(VehicleShareService)
    service.repository = MagicMock()
    return service


def test_enable_returns_existing_token() -> None:
    service = _service()
    service.repository.find_by_id.return_value = _vehicle(share_token='existing')

    assert service.enable(1) == 'existing'
    service.repository.set_share_token.assert_not_called()


def test_enable_generates_token() -> None:
    service = _service()
    service.repository.find_by_id.return_value = _vehicle()

    token = service.enable(1)

    assert token
    assert len(token) > 20
    service.repository.set_share_token.assert_called_once_with(1, token)


def test_enable_returns_none_for_missing_vehicle() -> None:
    service = _service()
    service.repository.find_by_id.return_value = None

    assert service.enable(1) is None
    service.repository.set_share_token.assert_not_called()


def test_rotate_replaces_token() -> None:
    service = _service()
    service.repository.find_by_id.return_value = _vehicle(share_token='old')

    token = service.rotate(1)

    assert token
    assert token != 'old'
    service.repository.set_share_token.assert_called_once_with(1, token)


def test_disable_clears_token() -> None:
    service = _service()
    service.repository.set_share_token.return_value = True

    assert service.disable(1) is True
    service.repository.set_share_token.assert_called_once_with(1, None)


def test_find_by_token_delegates_to_repository() -> None:
    service = _service()
    vehicle = _vehicle(share_token='tok')
    service.repository.find_by_share_token.return_value = vehicle

    assert service.find_by_token('tok') is vehicle
