from app.api.replacement.schema import ReplacementResponse
from app.common.enums import ComponentType, StatusEnum
from app.common.utils.calculator import StatusCalculator
from app.common.utils.interval_utils import add_months
from app.services.dto import ReplacementDTO, VehicleDTO


def build_replacement_response(
    replacement_dto: ReplacementDTO,
    vehicle: VehicleDTO,
    is_latest: bool = True,
) -> ReplacementResponse:
    """Преобразовать DTO замены в ответ с расчётом статуса."""
    is_tire = replacement_dto.component_type == ComponentType.TIRE_CHANGE

    if not is_latest:
        next_change_date = replacement_dto.next_change_date if is_tire else None
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
            next_change_date=next_change_date,
            days_remaining=None,
            status=StatusEnum.REPLACED.value,
        )

    if is_tire:
        status_data = StatusCalculator.calculate_date_status(
            replacement_dto.next_change_date,
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
            next_replacement_km=0,
            km_remaining=0,
            next_change_date=status_data["next_change_date"],
            days_remaining=status_data["days_remaining"],
            status=status_data["status"],
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
        next_change_date=next_change_date,
        days_remaining=days_remaining,
        status=status_data["status"],
    )
