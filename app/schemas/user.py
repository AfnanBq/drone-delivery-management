from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from .shared import Meta


class UserRole(StrEnum):
    ADMIN = "admin"
    ENDUSER = "enduser"
    DRONE = "drone"


class UserCreate(BaseModel):
    name: str
    role: UserRole


class UserBasic(BaseModel):
    id: int
    name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserToken(BaseModel):
    access_token: str
    token_type: str


class UserLogin(BaseModel):
    name: str
    role: UserRole


class UserListResponse(BaseModel):
    data: list[UserBasic]
    meta: Meta
