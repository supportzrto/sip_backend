from datetime import datetime
from uuid import UUID
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field,field_validator
import re
from app.auth.constants import UserRole, UserStatus


class RegisterRequest(BaseModel):
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain an uppercase letter.")

        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain a lowercase letter.")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain a number.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\\[\]]", value):
            raise ValueError("Password must contain a special character.")

        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    is_verified: bool
    created_at: datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Annotated[
        str,
        Field(min_length=12, max_length=128),
    ]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "Password must contain an uppercase letter."
            )

        if not re.search(r"[a-z]", value):
            raise ValueError(
                "Password must contain a lowercase letter."
            )

        if not re.search(r"\d", value):
            raise ValueError(
                "Password must contain a number."
            )

        if not re.search(
            r'[!@#$%^&*(),.?":{}|<>_\-+=/\\\[\]]',
            value,
        ):
            raise ValueError(
                "Password must contain a special character."
            )

        return value


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Annotated[str, Field(min_length=12)]

class LogoutRequest(BaseModel):
    refresh_token: str    