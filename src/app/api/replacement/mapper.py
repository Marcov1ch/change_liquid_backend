from app.api.replacement.schema import ReplacementResponse
from app.common.constants import get_date_warning_days
from app.common.enums import ComponentType, DATE_BASED_COMPONENT_TYPES, DATE_ONLY_COMPONENT_TYPES, StatusEnum
from app.common.utils.calculator import StatusCalculator
from app.common.utils.interval_utils import add_months
from app.services.dto import ReplacementDTO, VehicleDTO


def build_replacement_response(
    replacement_dto: ReplacementDTO,
    vehicle: VehicleDTO,
    is_latest: bool = True,
    km_traveled: int | None = None,
) -> ReplacementResponse:
    """Преобразовать DTO замены в ответ с расчётом статуса."""
    is_tire = replacement_dto.component_type == ComponentType.TIRE_CHANGE
    is_date_only = replacement_dto.component_type in DATE_ONLY_COMPONENT_TYPES
    is_date_based = replacement_dto.component_type in DATE_BASED_COMPONENT_TYPES
    if is_tire and km_traveled is None:
        km_traveled = max(0, vehicle.current_km - replacement_dto.km_at_replacement)
    if not is_tire:
        km_traveled = None

    if not is_latest:
        next_change_date = replacement_dto.next_change_date if is_date_based else None
        return ReplacementResponse(
            id=replacement_dto.id,
            vehicle_id=replacement_dto.vehicle_id,
            component_type=replacement_dto.component_type,
            component_name=replacement_dto.component_name,
            component_price=replacement_dto.component_price,
            work_price=replacement_dto.work_price,
            replacement_date=replacement_dto.replacement_date,
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=replacement_dto.interval_km,
            next_replacement_km=None,
            km_remaining=None,
            km_traveled=km_traveled,
            next_change_date=next_change_date,
            days_remaining=None,
            status=StatusEnum.REPLACED.value,
            source_repair_id=replacement_dto.source_repair_id,
        )

    if is_date_based:
        status_data = StatusCalculator.calculate_date_status(
            replacement_dto.next_change_date,
            get_date_warning_days(replacement_dto.component_type),
        )
        return ReplacementResponse(
            id=replacement_dto.id,
            vehicle_id=replacement_dto.vehicle_id,
            component_type=replacement_dto.component_type,
            component_name=replacement_dto.component_name,
            component_price=replacement_dto.component_price,
            work_price=replacement_dto.work_price,
            replacement_date=replacement_dto.replacement_date,
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=replacement_dto.interval_km,
            next_replacement_km=None if is_date_only else 0,
            km_remaining=None if is_date_only else 0,
            km_traveled=km_traveled,
            next_change_date=status_data["next_change_date"],
            days_remaining=status_data["days_remaining"],
            status=status_data["status"],
            source_repair_id=replacement_dto.source_repair_id,
        )

    interval = vehicle.intervals.get(replacement_dto.component_type.value, 0)
    status_data = StatusCalculator.calculate_status(
        km_at_replacement=replacement_dto.km_at_replacement,
        interval_km=interval,
        current_km=vehicle.current_km,
    )

    next_change_date = None
    days_remaining = None
    months = vehicle.interval_months.get(replacement_dto.component_type.value)
    if months is not None:
        next_change_date = add_months(replacement_dto.replacement_date, months)
        date_result = StatusCalculator.calculate_date_status(next_change_date)
        next_change_date = date_result["next_change_date"]
        days_remaining = date_result["days_remaining"]

    return ReplacementResponse(
        id=replacement_dto.id,
        vehicle_id=replacement_dto.vehicle_id,
        component_type=replacement_dto.component_type,
        component_name=replacement_dto.component_name,
        component_price=replacement_dto.component_price,
        work_price=replacement_dto.work_price,
        replacement_date=replacement_dto.replacement_date,
        km_at_replacement=replacement_dto.km_at_replacement,
        interval_km=replacement_dto.interval_km,
        next_replacement_km=status_data["next_replacement_km"],
        km_remaining=status_data["km_remaining"],
        km_traveled=km_traveled,
        next_change_date=next_change_date,
        days_remaining=days_remaining,
        status=status_data["status"],
        source_repair_id=replacement_dto.source_repair_id,
    )
