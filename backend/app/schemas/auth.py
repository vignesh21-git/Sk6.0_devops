from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    phone: str = Field(..., examples=["9876543210"])
    password: str = Field(..., min_length=6, max_length=72)
    full_name: str | None = Field(default=None, max_length=100)


class RegisterResponse(BaseModel):
    user_id: str
    phone: str
    status: str
    phone_verified: bool
    message: str = "OTP sent to your phone"


class RequestOtpRequest(BaseModel):
    phone: str


class RequestOtpResponse(BaseModel):
    phone: str
    expires_in_seconds: int


class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=10)


class VerifyOtpResponse(BaseModel):
    phone: str
    phone_verified: bool
    status: str


class LoginRequest(BaseModel):
    phone: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: str
    role: str


class LogoutResponse(BaseModel):
    message: str = "Logged out"
