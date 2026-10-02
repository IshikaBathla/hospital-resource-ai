from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.auth import UserRegister
from backend.utils.security import (
    hash_password,
    verify_password
)
from backend.utils.otp import (
    generate_otp,
    hash_otp,
    verify_otp
)


VALID_ROLES = {
    "ADMIN",
    "COORDINATOR",
    "STAFF",
    "VIEWER"
}

OTP_EXPIRY_MINUTES = 5

MAX_OTP_ATTEMPTS = 5


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
        return None, None, "Email already registered"

    role = user_data.role.upper()

    if role not in VALID_ROLES:
        return None, None, "Invalid role"

    user_count = db.query(User).count()

    user_id = f"U{1001 + user_count}"

    otp = generate_otp()

    user = User(
        user_id=user_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ),
        role=role,
        is_active=True,
        email_verified=False,
        otp_hash=hash_otp(otp),
        otp_expires_at=(
            datetime.utcnow()
            + timedelta(
                minutes=OTP_EXPIRY_MINUTES
            )
        ),
        otp_attempts="0"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, otp, None


def verify_email_otp(
    db: Session,
    email: str,
    otp: str
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        return None, "User not found"

    if user.email_verified:
        return None, "Email already verified"

    if not user.otp_hash:
        return None, "No OTP available"

    attempts = int(user.otp_attempts or "0")

    if attempts >= MAX_OTP_ATTEMPTS:
        return None, "Maximum OTP attempts exceeded"

    if (
        not user.otp_expires_at
        or datetime.utcnow() > user.otp_expires_at
    ):
        return None, "OTP has expired"

    if not verify_otp(
        otp,
        user.otp_hash
    ):

        user.otp_attempts = str(
            attempts + 1
        )

        db.commit()

        return None, "Invalid OTP"

    user.email_verified = True
    user.otp_hash = None
    user.otp_expires_at = None
    user.otp_attempts = "0"

    db.commit()
    db.refresh(user)

    return user, None


def generate_new_otp(
    db: Session,
    email: str
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        return None, None, "User not found"

    if user.email_verified:
        return None, None, "Email already verified"

    otp = generate_otp()

    user.otp_hash = hash_otp(otp)

    user.otp_expires_at = (
        datetime.utcnow()
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    )

    user.otp_attempts = "0"

    db.commit()
    db.refresh(user)

    return user, otp, None


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
        return None, "Invalid email or password"

    if not user.is_active:
        return None, "User account is inactive"

    if not user.email_verified:
        return None, "Email is not verified"

    if not verify_password(
        password,
        user.password_hash
    ):
        return None, "Invalid email or password"

    return user, None