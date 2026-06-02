from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str


class Meta(BaseModel):
    total: int
    per_page: int
    current_page: int
    last_page: int
    start: int
    end: int
