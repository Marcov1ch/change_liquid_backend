import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
)
from app.auth.rate_limit import (
    _client_ip,
    add_failed_attempt,
    check_rate_limit,
    clear_failed_attempts,
)
from app.auth.schemas import (
    RefreshRequest,
    RefreshTokenResponse,
    Token,
)
from app.auth.user_service import find_user_by_identifier, normalize_identifier
from app.db.database import get_db
from app.auth.password import verify_password

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Логин пользователя по username или email, возвращает JWT токен."""
    identifier = form_data.username
    key = f"{_client_ip(request)}:{normalize_identifier(identifier)}"

    if not check_rate_limit(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже."
        )

    user = find_user_by_identifier(db, identifier)

    if not user or not verify_password(form_data.password, user.hashed_password):
        add_failed_attempt(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )

    if not user.is_active:
        user.is_active = True
        db.commit()

    clear_failed_attempts(key)

    access_token = create_access_token(data={"sub": user.username}, version=user.token_version)
    refresh_token = create_refresh_token(data={"sub": user.username}, version=user.token_version)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
) -> RefreshTokenResponse:
    """Обновить access и refresh токены (сброс срока до 14 дней)."""
    try:
        tokens = refresh_access_token(db, request.refresh_token)
        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception('Failed to refresh tokens')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить токен",
        )
