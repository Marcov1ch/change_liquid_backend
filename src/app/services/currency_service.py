import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from app.common.enums import Currency

logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
_DEFAULT_TTL_SECONDS = 6 * 60 * 60
_DEFAULT_TIMEOUT_SECONDS = 5
_FALLBACK_RATES = {
    Currency.USD.value: 90.0,
    Currency.BYN.value: 27.5,
    Currency.EUR.value: 100.0,
}


@dataclass(frozen=True)
class RatesSnapshot:
    """Курсы валют и информация об источнике."""

    rates: dict[str, float]
    source: str
    fetched_at: datetime | None
    stale: bool


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _fallback_rates() -> dict[str, float]:
    return {
        Currency.RUB.value: 1.0,
        Currency.USD.value: _env_float("CURRENCY_FALLBACK_USD", _FALLBACK_RATES[Currency.USD.value]),
        Currency.BYN.value: _env_float("CURRENCY_FALLBACK_BYN", _FALLBACK_RATES[Currency.BYN.value]),
        Currency.EUR.value: _env_float("CURRENCY_FALLBACK_EUR", _FALLBACK_RATES[Currency.EUR.value]),
    }


class CurrencyRateService:
    """Загружает и кеширует курсы ЦБ РФ."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rates: dict[str, float] | None = None
        self._fetched_at: datetime | None = None
        self._source = "fallback"
        self._ttl_seconds = _env_int("CURRENCY_RATES_TTL_SECONDS", _DEFAULT_TTL_SECONDS)
        self._url = os.getenv("CURRENCY_RATES_URL", _DEFAULT_URL)
        self._timeout = _DEFAULT_TIMEOUT_SECONDS

    def _cache_is_fresh(self) -> bool:
        if self._fetched_at is None:
            return False
        age = (datetime.now(timezone.utc) - self._fetched_at).total_seconds()
        return age < self._ttl_seconds

    def _fetch_rates(self) -> dict[str, float]:
        request = Request(self._url, headers={"User-Agent": "ChangeLiquid/1.0"})
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        valute = payload.get("Valute") or {}
        rates: dict[str, float] = {Currency.RUB.value: 1.0}
        for code in (Currency.USD.value, Currency.BYN.value, Currency.EUR.value):
            item = valute.get(code)
            if not item:
                raise ValueError(f"Валюта {code} отсутствует в ответе ЦБ")
            nominal = float(item.get("Nominal") or 0)
            value = float(item.get("Value") or 0)
            if nominal <= 0 or value <= 0:
                raise ValueError(f"Некорректный курс для {code}")
            rates[code] = value / nominal
        return rates

    def get_rates(self) -> RatesSnapshot:
        """Вернуть актуальные курсы, при ошибке — кеш или fallback."""
        with self._lock:
            if self._rates is not None and self._cache_is_fresh():
                return RatesSnapshot(
                    rates=dict(self._rates),
                    source=self._source,
                    fetched_at=self._fetched_at,
                    stale=False,
                )

            try:
                rates = self._fetch_rates()
                self._rates = rates
                self._fetched_at = datetime.now(timezone.utc)
                self._source = "cbr"
                return RatesSnapshot(
                    rates=dict(rates),
                    source=self._source,
                    fetched_at=self._fetched_at,
                    stale=False,
                )
            except Exception:
                logger.warning('Failed to fetch currency rates, using cache or fallback', exc_info=True)
                if self._rates is not None:
                    return RatesSnapshot(
                        rates=dict(self._rates),
                        source=self._source,
                        fetched_at=self._fetched_at,
                        stale=True,
                    )
                return RatesSnapshot(
                    rates=_fallback_rates(),
                    source="fallback",
                    fetched_at=None,
                    stale=True,
                )

    def reset_cache(self) -> None:
        """Сбросить кеш (используется в тестах)."""
        with self._lock:
            self._rates = None
            self._fetched_at = None
            self._source = "fallback"


rate_service = CurrencyRateService()
