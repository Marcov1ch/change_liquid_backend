import pytest
from pydantic import ValidationError

from app.api.vehicle.schema import ReferenceItem, UpdateVehicleReference


def test_reference_item_accepts_volume_only() -> None:
    item = ReferenceItem(component_type='engine_oil', volume_liters=5.7)
    assert item.volume_liters == 5.7
    assert item.variants == []


def test_reference_item_accepts_variants_without_volume() -> None:
    item = ReferenceItem(
        component_type='cabin_filter',
        variants=[{'name': 'MANN CUK 2643', 'approvals': 'угольный'}],
    )
    assert item.volume_liters is None
    assert item.variants[0].name == 'MANN CUK 2643'


def test_reference_item_requires_volume_or_variant() -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(component_type='engine_oil')


def test_reference_item_rejects_unknown_component() -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(component_type='unknown_component', volume_liters=1)


def test_reference_item_rejects_non_positive_volume() -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(component_type='engine_oil', volume_liters=0)


def test_reference_item_rejects_blank_variant_name() -> None:
    with pytest.raises(ValidationError):
        ReferenceItem(component_type='engine_oil', variants=[{'name': '   '}])


def test_update_reference_rejects_duplicate_components() -> None:
    with pytest.raises(ValidationError):
        UpdateVehicleReference(reference_items=[
            {'component_type': 'engine_oil', 'volume_liters': 5.7},
            {'component_type': 'engine_oil', 'volume_liters': 5.0},
        ])
