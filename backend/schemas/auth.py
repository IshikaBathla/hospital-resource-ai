from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


class VerifyOTPRequest(BaseModel):
    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6
    )


class ResendOTPRequest(BaseModel):
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr

    password: str


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    is_active: bool
    email_verified: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse