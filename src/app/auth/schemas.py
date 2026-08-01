from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime


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


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


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


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MessageResponse(BaseModel):
    detail: str


class ForgotPasswordRequest(BaseModel):
    username: str
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
