from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Optional
from uuid import UUID

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class OrderStatus(StrEnum):
    SUBMITTED = "submitted"
    RESERVED = "reserved"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
    HANDOFF_REQUIRED = "handoff_required"
    HANDOFF_IN_PROGRESS = "handoff_in_progress"


class OrderCreateRequest(BaseModel):
    origin_location: list[float]
    destination_location: list[float]

    @model_validator(mode="after")
    def validate_coordinates(self):

        for coordinates in [
            self.origin_location,
            self.destination_location,
        ]:
            if len(coordinates) != 2:
                raise ValueError("coordinates must be [lng, lat]")

            lng, lat = coordinates

            if not (-180 <= float(lng) <= 180):
                raise ValueError("invalid longitude")

            if not (-90 <= float(lat) <= 90):
                raise ValueError("invalid latitude")

        return self


class OrderCreate(OrderCreateRequest):
    submitted_by_user_id: int
    status: OrderStatus = OrderStatus.SUBMITTED


class OrderBasic(BaseModel):
    id: UUID
    status: OrderStatus

    origin_location: dict[str, Any]
    destination_location: dict[str, Any]

    assigned_drone_id: Optional[UUID] = None
    submitted_by_user_id: int

    eta: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "origin_location",
        "destination_location",
        mode="before",
    )
    @classmethod
    def parse_location(cls, v):

        # already serialized
        if isinstance(v, dict):
            return v

        # PostGIS WKBElement → GeoJSON
        try:
            point = to_shape(v)

            return {
                "type": "Point",
                "coordinates": [point.x, point.y],
            }

        except Exception:
            return None


class OrderLocationUpdate(BaseModel):
    origin_location: Optional[list[float]] = None
    destination_location: Optional[list[float]] = None

    @model_validator(mode="after")
    def validate_coordinates(self):
        if not self.origin_location and not self.destination_location:
            raise ValueError("At least one complete location must be provided")

        for coordinates in [
            self.origin_location,
            self.destination_location,
        ]:
            if coordinates:
                if len(coordinates) != 2:
                    raise ValueError("coordinates must be [lng, lat]")

                lng, lat = coordinates

                if not (-180 <= float(lng) <= 180):
                    raise ValueError("invalid longitude")

                if not (-90 <= float(lat) <= 90):
                    raise ValueError("invalid latitude")
            return self


class OrderStatusUpdateRequest(BaseModel):
    event: Literal[OrderStatus.PICKED_UP, OrderStatus.DELIVERED, OrderStatus.FAILED]
    failure_reason: Optional[str] = None
