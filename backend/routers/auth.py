from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from backend.database import get_db
from backend.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse
)
from backend.services.auth_service import (
    create_user,
    authenticate_user,
    get_user_by_id
)
from backend.utils.security import (
    create_access_token,
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)


# ==========================================
# ROUTER CONFIGURATION
# ==========================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


# ==========================================
# REGISTER
# ==========================================

@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    user, error = create_user(
        db,
        user_data
    )

    if error:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return user


# ==========================================
# LOGIN
# ==========================================

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):

    user = authenticate_user(
        db,
        login_data.email,
        login_data.password
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
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


# ==========================================
# GET CURRENT USER
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db)
):

    # --------------------------------------
    # GET TOKEN
    # --------------------------------------

    token = credentials.credentials

    print(
        "AUTH HEADER RECEIVED:",
        credentials.scheme
    )

    print(
        "TOKEN RECEIVED:",
        token[:20] + "..."
        if token
        else "EMPTY"
    )

    # --------------------------------------
    # DECODE JWT
    # --------------------------------------

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        print(
            "JWT PAYLOAD:",
            payload
        )

        user_id = payload.get("sub")

        if not user_id:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token: user ID missing"
            )

    # --------------------------------------
    # TOKEN EXPIRED
    # --------------------------------------

    except jwt.ExpiredSignatureError:

        print(
            "JWT ERROR: Token has expired"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired"
        )

    # --------------------------------------
    # INVALID TOKEN
    # --------------------------------------

    except jwt.InvalidTokenError as e:

        print(
            "JWT ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

    # --------------------------------------
    # FIND USER
    # --------------------------------------

    user = get_user_by_id(
        db,
        user_id
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # --------------------------------------
    # CHECK ACTIVE STATUS
    # --------------------------------------

    if not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


# ==========================================
# CURRENT USER ENDPOINT
# ==========================================

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