import time
from datetime import datetime, timezone

import pytest
from starlette.requests import Request

import app.auth.handler as auth_handler
from app.auth.handler import (
    _client_ip,
    add_failed_attempt,
    check_rate_limit,
    failed_attempts,
)


@pytest.fixture(autouse=True)
def _reset_rate_limit_store(monkeypatch: pytest.MonkeyPatch) -> None:
    failed_attempts.clear()
    monkeypatch.setattr(auth_handler, "_last_cleanup", time.monotonic())


def _make_request(
    xff: str | None = None,
    client_host: str | None = "9.9.9.9",
) -> Request:
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    client = (client_host, 1234) if client_host else None
    scope = {
        "type": "http",
        "headers": headers,
        "client": client,
    }
    return Request(scope)


class TestClientIp:

    def test_uses_first_x_forwarded_for_value(self) -> None:
        request = _make_request(xff="1.2.3.4, 10.0.0.1")
        assert _client_ip(request) == "1.2.3.4"

    def test_falls_back_to_client_host(self) -> None:
        request = _make_request()
        assert _client_ip(request) == "9.9.9.9"

    def test_returns_unknown_without_ip(self) -> None:
        request = _make_request(client_host=None)
        assert _client_ip(request) == "unknown"


class TestRateLimit:

    def test_blocks_after_three_attempts(self) -> None:
        key = "1.2.3.4:user"
        assert check_rate_limit(key) is True
        add_failed_attempt(key)
        assert check_rate_limit(key) is True
        add_failed_attempt(key)
        assert check_rate_limit(key) is True
        add_failed_attempt(key)
        assert check_rate_limit(key) is False

    def test_key_is_isolated_by_ip_and_username(self) -> None:
        add_failed_attempt("1.2.3.4:user")
        add_failed_attempt("1.2.3.4:user")
        add_failed_attempt("1.2.3.4:user")
        assert check_rate_limit("1.2.3.4:user") is False
        assert check_rate_limit("5.6.7.8:user") is True
        assert check_rate_limit("1.2.3.4:other") is True

    def test_attempts_expire_after_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeDatetime(datetime):
            current = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

            @classmethod
            def now(cls, tz=None):
                return cls.current

        monkeypatch.setattr(auth_handler, "datetime", FakeDatetime)

        key = "1.2.3.4:user"
        add_failed_attempt(key)
        add_failed_attempt(key)
        add_failed_attempt(key)
        assert check_rate_limit(key) is False

        FakeDatetime.current = datetime(
            2024, 1, 1, 12, 5, 1, tzinfo=timezone.utc
        )
        assert check_rate_limit(key) is True

    def test_store_bounded_by_max_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_handler, "_RATE_LIMIT_MAX_KEYS", 3)
        for i in range(3):
            add_failed_attempt(f"ip{i}:user")

        assert check_rate_limit("ip-new:user") is True
        assert len(failed_attempts) <= 3
        assert "ip0:user" not in failed_attempts
