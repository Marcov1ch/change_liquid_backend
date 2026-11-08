from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.auth.schemas import UserCreate, UserResponse
from app.db.models import UserDB


def normalize_identifier(identifier: str) -> str:
    """Нормализовать идентификатор для rate limit и поиска по email."""
    return identifier.strip().lower()


def normalize_email(email: str) -> str:
    """Нормализовать email для хранения и сравнения."""
    return email.strip().lower()


def find_user_by_identifier(db: Session, identifier: str) -> UserDB | None:
    """Найти пользователя по username (точно) или email (без учёта регистра)."""
    user = db.query(UserDB).filter(UserDB.username == identifier).first()
    if user:
        return user

    email = normalize_identifier(identifier)
    if not email:
        return None

    return db.query(UserDB).filter(func.lower(UserDB.email) == email).first()


def find_user_by_id(db: Session, user_id: int) -> UserDB | None:
    """Найти пользователя по id."""
    return db.query(UserDB).filter(UserDB.id == user_id).first()


def user_to_response(user: UserDB) -> UserResponse:
    """Преобразовать ORM-модель пользователя в ответ API."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def registration_conflict_exists(db: Session, username: str, email: str) -> bool:
    """Проверить конфликты username/email при регистрации."""
    email = normalize_email(email)
    normalized_username = username.strip().lower()
    existing = db.query(UserDB).filter(
        (UserDB.username == username)
        | (func.lower(UserDB.email) == email)
        | (func.lower(UserDB.email) == normalized_username)
        | (func.lower(UserDB.username) == email)
    ).first()
    return existing is not None


def email_conflict_exists(
    db: Session,
    email: str,
    exclude_user_id: int | None = None,
) -> bool:
    """Проверить, занят ли email или совпадает с username другого пользователя."""
    email = normalize_email(email)
    query = db.query(UserDB).filter(
        (func.lower(UserDB.email) == email)
        | (func.lower(UserDB.username) == email)
    )
    if exclude_user_id is not None:
        query = query.filter(UserDB.id != exclude_user_id)
    return query.first() is not None


def create_user(db: Session, user_data: UserCreate) -> UserDB:
    """Создать нового пользователя."""
    new_user = UserDB(
        username=user_data.username,
        email=normalize_email(str(user_data.email)),
        hashed_password=hash_password(user_data.password),
        email_verified=False,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
