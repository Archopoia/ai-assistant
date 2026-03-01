from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    email_verified: bool
    two_factor_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20)


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TwoFactorDisableRequest(BaseModel):
    code: Optional[str] = Field(default=None, min_length=6, max_length=6)


class TwoFactorVerifyLoginRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
