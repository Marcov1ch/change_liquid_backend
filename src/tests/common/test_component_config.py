import pytest

from app.common.component_config import COMPONENTS_CONFIG, ComponentConfig
from app.common.enums import ComponentType
from app.db.models import VehicleDB

CONFIGURED_COMPONENTS = [cfg.type for cfg in COMPONENTS_CONFIG]


def test_every_component_type_is_configured() -> None:
    """Каждый отслеживаемый компонент, кроме шин, описан в COMPONENTS_CONFIG."""
    expected = {t for t in ComponentType if t != ComponentType.TIRE_CHANGE}
    assert set(CONFIGURED_COMPONENTS) == expected


def test_config_has_no_duplicates() -> None:
    assert len(CONFIGURED_COMPONENTS) == len(set(CONFIGURED_COMPONENTS))


@pytest.mark.parametrize('cfg', COMPONENTS_CONFIG, ids=[cfg.type.value for cfg in COMPONENTS_CONFIG])
def test_config_fields_match_orm_columns(cfg: ComponentConfig) -> None:
    """Имена полей конфигурации должны соответствовать колонкам VehicleDB."""
    months_field = cfg.interval_field.replace('_km', '_months')
    assert hasattr(VehicleDB, cfg.interval_field)
    assert hasattr(VehicleDB, cfg.notify_field)
    assert hasattr(VehicleDB, months_field)


@pytest.mark.parametrize('cfg', COMPONENTS_CONFIG, ids=[cfg.type.value for cfg in COMPONENTS_CONFIG])
def test_config_values_are_valid(cfg: ComponentConfig) -> None:
    assert cfg.default_interval > 0
    assert cfg.name.strip()
    assert cfg.name_genitive.strip()
    assert cfg.example.strip()
    if cfg.default_interval_months is not None:
        assert cfg.default_interval_months > 0


def test_fuel_filter_config() -> None:
    cfg = next(c for c in COMPONENTS_CONFIG if c.type == ComponentType.FUEL_FILTER)
    assert cfg.name == 'Топливный фильтр'
    assert cfg.name_genitive == 'топливного фильтра'
    assert cfg.default_interval == 50000
    assert cfg.default_interval_months == 24
