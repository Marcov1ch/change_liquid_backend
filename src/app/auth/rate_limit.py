import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status

_RATE_LIMIT_ATTEMPTS = 3
_RATE_LIMIT_WINDOW_SECONDS = 300
_RATE_LIMIT_MAX_KEYS = 10000
_RATE_LIMIT_CLEANUP_SECONDS = 60

_RESEND_VERIFICATION_COOLDOWN_SECONDS = 60
_RESEND_VERIFICATION_MAX_KEYS = 10000

failed_attempts: defaultdict[str, list[datetime]] = defaultdict(list)
resend_cooldowns: dict[str, datetime] = {}
_last_cleanup = time.monotonic()


def _client_ip(request: Request) -> str:
    """Взять реальный IP клиента, учитывая X-Forwarded-For за прокси."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _prune_stale() -> None:
    """Периодически удалять ключи с пустыми списками попыток."""
    global _last_cleanup
    if time.monotonic() - _last_cleanup < _RATE_LIMIT_CLEANUP_SECONDS:
        return
    _last_cleanup = time.monotonic()
    empty = [key for key, value in failed_attempts.items() if not value]
    for key in empty:
        del failed_attempts[key]


def check_rate_limit(key: str) -> bool:
    """Проверить, не превышен ли лимит попыток входа."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)
    failed_attempts[key] = [item for item in failed_attempts[key] if item >= cutoff]

    _prune_stale()

    if len(failed_attempts[key]) >= _RATE_LIMIT_ATTEMPTS:
        return False

    if len(failed_attempts) > _RATE_LIMIT_MAX_KEYS:
        while len(failed_attempts) > _RATE_LIMIT_MAX_KEYS:
            failed_attempts.pop(next(iter(failed_attempts)))

    return True


def add_failed_attempt(key: str) -> None:
    """Добавить неудачную попытку входа."""
    failed_attempts[key].append(datetime.now(timezone.utc))


def clear_failed_attempts(key: str) -> None:
    """Сбросить неудачные попытки для ключа."""
    failed_attempts.pop(key, None)


def _prune_resend_cooldowns() -> None:
    """Удалить истёкшие кулдауны повторной отправки письма."""
    now = datetime.now(timezone.utc)
    expired = [key for key, until in resend_cooldowns.items() if until <= now]
    for key in expired:
        del resend_cooldowns[key]

    while len(resend_cooldowns) > _RESEND_VERIFICATION_MAX_KEYS:
        resend_cooldowns.pop(next(iter(resend_cooldowns)))


def _resend_cooldown_remaining(user_id: int) -> int:
    """Вернуть оставшееся время кулдауна в секундах."""
    until = resend_cooldowns.get(str(user_id))
    if not until:
        return 0
    remaining = (until - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(remaining + 0.999))


def _check_resend_cooldown(user_id: int) -> None:
    """Запретить повторную отправку письма раньше окончания кулдауна."""
    remaining = _resend_cooldown_remaining(user_id)
    if remaining > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Повторно отправить письмо можно через {remaining} сек.",
            headers={"Retry-After": str(remaining)},
        )
    _prune_resend_cooldowns()


def _mark_verification_sent(user_id: int) -> None:
    """Запустить кулдаун после отправки письма подтверждения."""
    resend_cooldowns[str(user_id)] = (
        datetime.now(timezone.utc)
        + timedelta(seconds=_RESEND_VERIFICATION_COOLDOWN_SECONDS)
    )
