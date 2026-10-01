from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.auth import UserRegister
from backend.utils.security import (
    hash_password,
    verify_password
)


VALID_ROLES = {
    "ADMIN",
    "COORDINATOR",
    "STAFF",
    "VIEWER"
}


def get_user_by_email(
    db: Session,
    email: str
):
    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: str
):
    return (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )


def create_user(
    db: Session,
    user_data: UserRegister
):

    existing_user = get_user_by_email(
        db,
        user_data.email
    )

    if existing_user:
        return None, "Email already registered"

    role = user_data.role.upper()

    if role not in VALID_ROLES:
        return None, "Invalid role"

    user_count = db.query(User).count()

    user_id = f"U{1001 + user_count}"

    user = User(
        user_id=user_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ),
        role=role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, None


def authenticate_user(
    db: Session,
    email: str,
    password: str
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user