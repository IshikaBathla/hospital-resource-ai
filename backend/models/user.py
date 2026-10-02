from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(20), primary_key=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(30),
        nullable=False,
        default="VIEWER"
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True
    )

    email_verified = Column(
        Boolean,
        nullable=False,
        default=False
    )

    otp_hash = Column(
        String(255),
        nullable=True
    )

    otp_expires_at = Column(
        DateTime,
        nullable=True
    )

    otp_attempts = Column(
        String(10),
        nullable=False,
        default="0"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )