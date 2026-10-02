from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy.orm import Session

import jwt

from backend.database import get_db

from backend.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    VerifyOTPRequest,
    ResendOTPRequest
)

from backend.services.auth_service import (
    create_user,
    authenticate_user,
    get_user_by_id,
    verify_email_otp,
    generate_new_otp
)

from backend.utils.security import (
    create_access_token,
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    user, otp, error = create_user(
        db,
        user_data
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # DEVELOPMENT ONLY:
    # OTP is returned so that we can test
    # without configuring an email provider.
    return user


@router.post("/verify-email")
def verify_email(
    data: VerifyOTPRequest,
    db: Session = Depends(get_db)
):

    user, error = verify_email_otp(
        db,
        data.email,
        data.otp
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return {
        "message": "Email verified successfully",
        "user_id": user.user_id,
        "email": user.email,
        "email_verified": user.email_verified
    }


@router.post("/resend-otp")
def resend_otp(
    data: ResendOTPRequest,
    db: Session = Depends(get_db)
):

    user, otp, error = generate_new_otp(
        db,
        data.email
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # DEVELOPMENT ONLY
    return {
        "message": "OTP generated successfully",
        "email": user.email,
        "otp": otp
    }


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):

    user, error = authenticate_user(
        db,
        login_data.email,
        login_data.password
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )

    token = create_access_token(
        user_id=user.user_id,
        role=user.role
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    user = get_user_by_id(
        db,
        user_id
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


def require_roles(*allowed_roles):

    def role_checker(
        current_user=Depends(
            get_current_user
        )
    ):

        user_role = current_user.role.upper()

        normalized_roles = {
            role.upper()
            for role in allowed_roles
        }

        if user_role not in normalized_roles:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to perform this action"
                )
            )

        return current_user

    return role_checker


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user=Depends(
        get_current_user
    )
):

    return current_user


@router.get("/admin-test")
def admin_test(
    current_user=Depends(
        require_roles("ADMIN")
    )
):

    return {
        "message": "Admin access granted",
        "user_id": current_user.user_id,
        "role": current_user.role
    }