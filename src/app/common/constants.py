from typing import Final

from app.common.enums import ComponentType

DATE_WARNING_DAYS: Final[int] = 5
DATE_WARNING_DAYS_BY_COMPONENT: Final[dict[str, int]] = {
    ComponentType.PARKING_MONTHLY.value: 1,
}


def get_date_warning_days(component_type: ComponentType | str) -> int:
    """Вернуть количество дней для предупреждения по date-based компоненту."""
    key = component_type.value if isinstance(component_type, ComponentType) else component_type
    return DATE_WARNING_DAYS_BY_COMPONENT.get(key, DATE_WARNING_DAYS)
