import bcrypt


def hash_password(password: str) -> str:
    """Хеширует пароль с помощью bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль на соответствие хешу."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
