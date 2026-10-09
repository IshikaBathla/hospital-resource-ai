
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    VerifyOTPRequest,
    ResendOTPRequest,
)
from backend.services.auth_service import (
    create_user,
    authenticate_user,
    verify_email_otp,
    generate_new_otp,
)
from backend.services.email_service import send_verification_otp
from backend.utils.security import create_access_token
from backend.utils.dependencies import get_current_user, require_roles


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    user, otp, error = create_user(db, user_data)

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    email_sent = send_verification_otp(user.email, otp)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Account created but verification email could not be sent. "
                "Check SMTP configuration, then request a new OTP."
            ),
        )

    return {
        "message": "Account created. Check your email for the verification code.",
        "email": user.email,
        "email_verified": False,
    }


@router.post("/verify-email")
def verify_email(
    data: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    user, error = verify_email_otp(
        db,
        data.email.strip().lower(),
        data.otp,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return {
        "message": "Email verified successfully. You can now sign in.",
        "user_id": user.user_id,
        "email": user.email,
        "email_verified": user.email_verified,
    }


@router.post("/resend-otp")
def resend_otp(
    data: ResendOTPRequest,
    db: Session = Depends(get_db),
):
    user, otp, error = generate_new_otp(
        db,
        data.email.strip().lower(),
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    email_sent = send_verification_otp(user.email, otp)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email could not be sent. Check SMTP configuration.",
        )

    return {
        "message": "Verification code sent to your email."
    }


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    user, error = authenticate_user(
        db,
        login_data.email.strip().lower(),
        login_data.password,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    token = create_access_token(
        user_id=user.user_id,
        role=user.role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user=Depends(get_current_user),
):
    return current_user


@router.get("/admin-test")
def admin_test(
    current_user=Depends(require_roles("ADMIN")),
):
    return {
        "message": "Admin access granted",
        "user_id": current_user.user_id,
        "role": current_user.role,
    }
