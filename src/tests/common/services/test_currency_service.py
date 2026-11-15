from datetime import datetime, timedelta, timezone
import json
from unittest.mock import MagicMock, patch

from app.services.currency_service import CurrencyRateService

_PAYLOAD = {
    "Valute": {
        "USD": {"Nominal": 1, "Value": 90.5},
        "BYN": {"Nominal": 1, "Value": 28.2},
        "EUR": {"Nominal": 1, "Value": 100.7},
    },
}


def _response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    return response


def test_fetch_rates_divides_by_nominal() -> None:
    service = CurrencyRateService()
    payload = {
        "Valute": {
            "USD": {"Nominal": 2, "Value": 180.0},
            "BYN": {"Nominal": 1, "Value": 28.0},
            "EUR": {"Nominal": 10, "Value": 1000.0},
        },
    }

    with patch('app.services.currency_service.urlopen', return_value=_response(payload)):
        rates = service._fetch_rates()

    assert rates['RUB'] == 1.0
    assert rates['USD'] == 90.0
    assert rates['BYN'] == 28.0
    assert rates['EUR'] == 100.0


def test_get_rates_uses_cache() -> None:
    service = CurrencyRateService()
    calls = 0

    def fake_fetch() -> dict[str, float]:
        nonlocal calls
        calls += 1
        return {'RUB': 1.0, 'USD': 90.0, 'BYN': 28.0, 'EUR': 100.0}

    with patch.object(service, '_fetch_rates', side_effect=fake_fetch):
        first = service.get_rates()
        second = service.get_rates()

    assert first.stale is False
    assert second.stale is False
    assert calls == 1


def test_get_rates_returns_stale_cache_on_error() -> None:
    service = CurrencyRateService()
    service._rates = {'RUB': 1.0, 'USD': 80.0, 'BYN': 25.0, 'EUR': 90.0}
    service._fetched_at = datetime.now(timezone.utc) - timedelta(days=1)
    service._source = 'cbr'

    with patch.object(service, '_fetch_rates', side_effect=RuntimeError('network')):
        snapshot = service.get_rates()

    assert snapshot.stale is True
    assert snapshot.rates['USD'] == 80.0
    assert snapshot.source == 'cbr'


def test_get_rates_returns_fallback_without_cache() -> None:
    service = CurrencyRateService()

    with patch.object(service, '_fetch_rates', side_effect=RuntimeError('network')):
        snapshot = service.get_rates()

    assert snapshot.stale is True
    assert snapshot.source == 'fallback'
    assert snapshot.fetched_at is None
    assert set(snapshot.rates) == {'RUB', 'USD', 'BYN', 'EUR'}
