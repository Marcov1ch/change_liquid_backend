import pytest
from pydantic import ValidationError

from app.auth.schemas import UserCreate


class TestUserCreateControlChars:

    def test_rejects_control_characters_in_username(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(username='user\r\nx', email='user@example.com', password='secret')

    def test_allows_normal_username(self) -> None:
        user = UserCreate(username='user1', email='user@example.com', password='secret')
        assert user.username == 'user1'
