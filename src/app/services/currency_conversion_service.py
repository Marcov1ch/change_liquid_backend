import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.common.enums import Currency
from app.db.models import (
    FuelRecordDB,
    OtherExpenseDB,
    RepairDB,
    ReplacementDB,
    TireSetDB,
    UserDB,
    VehicleDB,
)
from app.services.currency_service import CurrencyRateService, rate_service

_ZERO = Decimal("0.00")
_QUANT = Decimal("0.01")
_conversion_lock = threading.Lock()


class CurrencyRateError(ValueError):
    """Не удалось получить курс для конвертации."""


@dataclass(frozen=True)
class ConversionPreview:
    """Данные для подтверждения смены валюты."""

    from_currency: str
    to_currency: str
    rate: float | None
    to_rub_rate: float | None
    records_count: int
    vehicles_count: int
    source: str
    fetched_at: datetime | None
    stale: bool


@dataclass(frozen=True)
class ConversionResult:
    """Результат фактической смены валюты."""

    from_currency: str
    to_currency: str
    rate: float | None
    records_count: int
    source: str
    stale: bool


def _as_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _convert(value: object, factor: Decimal) -> Decimal | None:
    number = _as_decimal(value)
    if number is None:
        return None
    return (number * factor).quantize(_QUANT, rounding=ROUND_HALF_UP)


class CurrencyConversionService:
    """Смена валюты пользователя с пересчётом денежных значений."""

    def __init__(
        self,
        db: Session,
        rates: CurrencyRateService | None = None,
    ) -> None:
        self.db = db
        self.rates = rates or rate_service

    def convert_amounts(
        self,
        values: list[float | None],
        source: str,
        target: str,
    ) -> list[float | None]:
        """Пересчитать суммы из source в target по текущему курсу."""
        if source == target:
            return list(values)

        snapshot = self.rates.get_rates()
        rate_from = snapshot.rates.get(source)
        rate_to = snapshot.rates.get(target)
        if rate_from is None or rate_to is None:
            raise CurrencyRateError('Не удалось получить курс для выбранной валюты')

        factor = Decimal(str(rate_from)) / Decimal(str(rate_to))
        result: list[float | None] = []
        for value in values:
            converted = _convert(value, factor)
            result.append(None if converted is None else float(converted))
        return result

    def convert_for_owner(
        self,
        values: list[float | None],
        requested: Currency | None,
        owner_currency: str,
    ) -> list[float | None]:
        """Пересчитать суммы из валюты ввода в валюту владельца."""
        target = owner_currency or Currency.RUB.value
        source = requested.value if requested is not None else target
        return self.convert_amounts(values, source, target)

    def _vehicle_ids(self, user_id: int) -> list[int]:
        rows = self.db.query(VehicleDB.id).filter(VehicleDB.owner_id == user_id).all()
        return [int(row[0]) for row in rows]

    def _money_vehicle_ids(self, vehicle_ids: list[int]) -> set[int]:
        if not vehicle_ids:
            return set()

        result: set[int] = set()

        replacement_rows = self.db.query(ReplacementDB.vehicle_id).filter(
            ReplacementDB.vehicle_id.in_(vehicle_ids),
            or_(
                ReplacementDB.component_price.isnot(None),
                ReplacementDB.work_price.isnot(None),
            ),
        ).distinct().all()
        result.update(int(row[0]) for row in replacement_rows)

        tire_rows = self.db.query(TireSetDB.vehicle_id).filter(
            TireSetDB.vehicle_id.in_(vehicle_ids),
            TireSetDB.purchase_price.isnot(None),
        ).distinct().all()
        result.update(int(row[0]) for row in tire_rows)

        for model in (RepairDB, FuelRecordDB, OtherExpenseDB):
            rows = self.db.query(model.vehicle_id).filter(
                model.vehicle_id.in_(vehicle_ids),
            ).distinct().all()
            result.update(int(row[0]) for row in rows)

        return result

    def _money_records_count(self, vehicle_ids: list[int]) -> int:
        if not vehicle_ids:
            return 0

        count = 0
        count += self.db.query(func.count(ReplacementDB.id)).filter(
            ReplacementDB.vehicle_id.in_(vehicle_ids),
            or_(
                ReplacementDB.component_price.isnot(None),
                ReplacementDB.work_price.isnot(None),
            ),
        ).scalar() or 0
        count += self.db.query(func.count(TireSetDB.id)).filter(
            TireSetDB.vehicle_id.in_(vehicle_ids),
            TireSetDB.purchase_price.isnot(None),
        ).scalar() or 0
        for model in (RepairDB, FuelRecordDB, OtherExpenseDB):
            count += self.db.query(func.count(model.id)).filter(
                model.vehicle_id.in_(vehicle_ids),
            ).scalar() or 0
        return int(count)

    def _convert_all(self, vehicle_ids: list[int], factor: Decimal) -> None:
        if not vehicle_ids:
            return

        replacements = self.db.query(ReplacementDB).filter(
            ReplacementDB.vehicle_id.in_(vehicle_ids),
        ).all()
        for row in replacements:
            row.component_price = _convert(row.component_price, factor)
            row.work_price = _convert(row.work_price, factor)

        tire_sets = self.db.query(TireSetDB).filter(
            TireSetDB.vehicle_id.in_(vehicle_ids),
        ).all()
        for row in tire_sets:
            row.purchase_price = _convert(row.purchase_price, factor)

        repairs = self.db.query(RepairDB).filter(
            RepairDB.vehicle_id.in_(vehicle_ids),
        ).all()
        for row in repairs:
            row.work_cost = _convert(row.work_cost, factor) or _ZERO
            row.parts_cost = _convert(row.parts_cost, factor) or _ZERO

        fuel_records = self.db.query(FuelRecordDB).filter(
            FuelRecordDB.vehicle_id.in_(vehicle_ids),
        ).all()
        for row in fuel_records:
            row.total_cost = _convert(row.total_cost, factor) or _ZERO

        other_expenses = self.db.query(OtherExpenseDB).filter(
            OtherExpenseDB.vehicle_id.in_(vehicle_ids),
        ).all()
        for row in other_expenses:
            row.amount = _convert(row.amount, factor) or _ZERO

    def preview(self, user: UserDB, target: str) -> ConversionPreview:
        from_currency = user.currency or Currency.RUB.value
        vehicle_ids = self._vehicle_ids(user.id)
        records_count = self._money_records_count(vehicle_ids)
        money_vehicles = self._money_vehicle_ids(vehicle_ids)

        if from_currency == target:
            return ConversionPreview(
                from_currency=from_currency,
                to_currency=target,
                rate=1.0,
                to_rub_rate=None,
                records_count=records_count,
                vehicles_count=len(money_vehicles),
                source="none",
                fetched_at=None,
                stale=False,
            )

        snapshot = self.rates.get_rates()
        rate_from = snapshot.rates.get(from_currency)
        rate_to = snapshot.rates.get(target)
        if rate_from is None or rate_to is None:
            raise ValueError("Не удалось получить курс для выбранной валюты")

        return ConversionPreview(
            from_currency=from_currency,
            to_currency=target,
            rate=rate_from / rate_to,
            to_rub_rate=rate_to,
            records_count=records_count,
            vehicles_count=len(money_vehicles),
            source=snapshot.source,
            fetched_at=snapshot.fetched_at,
            stale=snapshot.stale,
        )

    def apply(self, user: UserDB, target: str) -> ConversionResult:
        with _conversion_lock:
            return self._apply_locked(user, target)

    def _apply_locked(self, user: UserDB, target: str) -> ConversionResult:
        self.db.refresh(user)
        from_currency = user.currency or Currency.RUB.value
        vehicle_ids = self._vehicle_ids(user.id)

        try:
            if from_currency == target:
                records_count = self._money_records_count(vehicle_ids)
                user.currency = target
                self.db.commit()
                return ConversionResult(
                    from_currency=from_currency,
                    to_currency=target,
                    rate=1.0,
                    records_count=records_count,
                    source="none",
                    stale=False,
                )

            records_count = self._money_records_count(vehicle_ids)
            if records_count == 0:
                user.currency = target
                self.db.commit()
                return ConversionResult(
                    from_currency=from_currency,
                    to_currency=target,
                    rate=None,
                    records_count=0,
                    source="none",
                    stale=False,
                )

            snapshot = self.rates.get_rates()
            rate_from = snapshot.rates.get(from_currency)
            rate_to = snapshot.rates.get(target)
            if rate_from is None or rate_to is None:
                raise ValueError("Не удалось получить курс для выбранной валюты")

            factor = Decimal(str(rate_from)) / Decimal(str(rate_to))
            self._convert_all(vehicle_ids, factor)
            user.currency = target
            self.db.commit()

            return ConversionResult(
                from_currency=from_currency,
                to_currency=target,
                rate=float(factor),
                records_count=records_count,
                source=snapshot.source,
                stale=snapshot.stale,
            )
        except Exception:
            self.db.rollback()
            raise
