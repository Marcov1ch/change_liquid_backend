from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

from app.common.enums import Currency


class UserCreate(BaseModel):
    """Схема для регистрации пользователя."""
    username: str
    email: EmailStr
    password: str

    @field_validator('username')
    @classmethod
    def validate_no_control_chars(cls, v: str) -> str:
        if any(ord(ch) < 32 for ch in v):
            raise ValueError('Имя пользователя не может содержать управляющие символы')
        return v

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    id: int
    username: str
    email: str
    email_verified: bool
    is_active: bool
    currency: str
    profile_visited: bool
    created_at: datetime


class UpdateCurrencyRequest(BaseModel):
    """Смена валюты текущего пользователя."""
    currency: Currency


class CurrencyChangeResponse(BaseModel):
    """Результат смены валюты."""
    user: UserResponse
    from_currency: str
    to_currency: str
    rate: float | None = None
    records_count: int = 0
    source: str
    stale: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    """Данные, хранящиеся в токене."""
    username: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateEmailRequest(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MessageResponse(BaseModel):
    detail: str


class ForgotPasswordRequest(BaseModel):
    username: str
    email: EmailStr

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str
