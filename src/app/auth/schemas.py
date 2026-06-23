from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    """Схема для регистрации пользователя."""
    username: str
    email: EmailStr
    password: str


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
