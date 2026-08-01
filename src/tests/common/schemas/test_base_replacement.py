import pytest
from pydantic import ValidationError

from app.common.enums import ComponentType
from app.common.schemas.base_replacement import ReplacementBase


class TestReplacementBaseControlChars:

    def test_rejects_control_characters_in_component_name(self) -> None:
        with pytest.raises(ValidationError):
            ReplacementBase(
                component_type=ComponentType.ENGINE_OIL,
                component_name='Mobil 1\r\nBcc: x',
            )

    def test_allows_normal_component_name(self) -> None:
        item = ReplacementBase(
            component_type=ComponentType.ENGINE_OIL,
            component_name='Mobil 1 5W-30',
        )
        assert item.component_name == 'Mobil 1 5W-30'
