import secrets

from backend.utils.security import (
    hash_password,
    verify_password
)


def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str) -> str:
    return hash_password(otp)


def verify_otp(
    otp: str,
    otp_hash: str
) -> bool:

    return verify_password(
        otp,
        otp_hash
    )