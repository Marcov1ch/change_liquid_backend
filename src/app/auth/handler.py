import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.db.models import UserDB
from app.auth.password import hash_password, verify_password
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    get_current_user,
)
from app.auth.schemas import (
    RefreshRequest,
    UserCreate,
    UserResponse,
    Token,
    RefreshTokenResponse,
    UpdateEmailRequest,
    ChangePasswordRequest,
    MessageResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.email_service import send_reset_password_email
from app.auth.jwt import (
    SECRET_KEY,
    ALGORITHM,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

_RATE_LIMIT_ATTEMPTS = 3
_RATE_LIMIT_WINDOW_SECONDS = 300
_RATE_LIMIT_MAX_KEYS = 10000
_RATE_LIMIT_CLEANUP_SECONDS = 60

failed_attempts: defaultdict[str, list[datetime]] = defaultdict(list)
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
    empty = [k for k, v in failed_attempts.items() if not v]
    for k in empty:
        del failed_attempts[k]


def check_rate_limit(key: str) -> bool:
    """Проверяет, не превышен ли лимит попыток входа (3 попытки за 5 минут на ip:username)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)
    failed_attempts[key] = [t for t in failed_attempts[key] if t >= cutoff]

    _prune_stale()

    if len(failed_attempts[key]) >= _RATE_LIMIT_ATTEMPTS:
        return False

    if len(failed_attempts) > _RATE_LIMIT_MAX_KEYS:
        while len(failed_attempts) > _RATE_LIMIT_MAX_KEYS:
            failed_attempts.pop(next(iter(failed_attempts)))

    return True


def add_failed_attempt(key: str) -> None:
    """Добавляет неудачную попытку входа."""
    failed_attempts[key].append(datetime.now(timezone.utc))


def _send_reset_password_email_safe(to_email: str, token: str) -> None:
    """Отправить письмо восстановления пароля, не роняя фоновую задачу."""
    try:
        send_reset_password_email(to_email=to_email, token=token)
    except Exception:
        logger.exception('Failed to send reset-password email to %s', to_email)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Регистрация нового пользователя."""
    existing = db.query(UserDB).filter(
        (UserDB.username == user_data.username) | (UserDB.email == user_data.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя или email уже заняты"
        )

    hashed = hash_password(user_data.password)
    new_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    """Логин пользователя, возвращает JWT токен."""
    username = form_data.username
    key = f"{_client_ip(request)}:{username}"

    if not check_rate_limit(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже."
        )

    user = db.query(UserDB).filter(UserDB.username == username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        add_failed_attempt(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )

    if not user.is_active:
        user.is_active = True
        db.commit()

    failed_attempts.pop(key, None)

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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserDB = Depends(get_current_user)) -> UserResponse:
    """Получить информацию о текущем пользователе."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.patch("/email", response_model=UserResponse)
async def update_email(
    request: UpdateEmailRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> UserResponse:
    """Сменить email текущего пользователя."""
    existing = db.query(UserDB).filter(
        UserDB.email == request.email,
        UserDB.id != current_user.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже используется"
        )

    current_user.email = request.email
    current_user.token_version += 1
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Сменить пароль текущего пользователя."""
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль"
        )

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен отличаться от старого"
        )

    current_user.hashed_password = hash_password(request.new_password)
    current_user.token_version += 1
    db.commit()

    return MessageResponse(detail="Пароль успешно изменён")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Деактивировать аккаунт (soft delete)."""
    current_user.is_active = False
    current_user.token_version += 1
    db.commit()

    return MessageResponse(detail="Аккаунт деактивирован")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Отправить письмо для восстановления пароля."""
    user = db.query(UserDB).filter(
        UserDB.username == request.username,
        UserDB.email == request.email,
    ).first()

    if not user:
        return MessageResponse(
            detail="Если такой email зарегистрирован, письмо отправлено"
        )

    reset_token = jwt.encode(
        {
            "sub": user.email,
            "type": "password_reset",
            "ver": user.token_version,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    background_tasks.add_task(
        _send_reset_password_email_safe,
        to_email=user.email,
        token=reset_token,
    )

    return MessageResponse(
        detail="Если такой email зарегистрирован, письмо отправлено"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Сбросить пароль по токену."""
    try:
        payload = verify_token(request.token, "password_reset")
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный токен",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный или просроченный токен",
        )

    user = db.query(UserDB).filter(UserDB.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не найден",
        )

    if payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный или просроченный токен",
        )

    user.hashed_password = hash_password(request.new_password)
    user.token_version += 1
    db.commit()

    return MessageResponse(detail="Пароль успешно изменён")
