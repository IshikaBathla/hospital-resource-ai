
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "local-development-only-change-me-before-deployment",
)

APP_ENV = os.getenv("APP_ENV", "development").lower()

if (
    JWT_SECRET_KEY == "local-development-only-change-me-before-deployment"
    and APP_ENV == "production"
):
    raise RuntimeError(
        "Set a strong JWT_SECRET_KEY in production environment variables."
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
