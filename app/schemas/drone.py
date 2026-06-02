import logging
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely.wkb import loads as wkb_loads

from .shared import Meta

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


class DroneStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    BROKEN = "broken"
    FIXED = "fixed"


class DroneCreate(BaseModel):
    user_id: int
    status: DroneStatus
    location: list[float] = Field(default_factory=lambda: [39.1925, 21.4858])  # Jeddah [lng, lat]

    @field_validator("location")
    @classmethod
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError("coordinates must be [lng, lat]")

        lng, lat = v

        if not (-180 <= float(lng) <= 180):
            raise ValueError("invalid longitude")

        if not (-90 <= float(lat) <= 90):
            raise ValueError("invalid latitude")

        return [float(lng), float(lat)]


class DroneBasic(BaseModel):
    id: UUID
    user_id: int
    status: str
    location: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("location", mode="before")
    @classmethod
    def parse_location(cls, v):
        # already serialized
        if isinstance(v, dict):
            return v

        # PostGIS WKBElement → GeoJSON
        try:
            if isinstance(v, (str, bytes)):
                bytes_data = bytes.fromhex(v) if isinstance(v, str) else v
                point = wkb_loads(bytes_data, hex=isinstance(v, str))
            else:
                point = to_shape(v)
            return {
                "type": "Point",
                "coordinates": [point.x, point.y],
            }

        except Exception:
            logger.error("Failed to parse location WKBElement: %s", v)
            return None


class UpdateLocationRequest(BaseModel):
    location: list[float]

    @field_validator("location")
    @classmethod
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError("coordinates must be [lng, lat]")

        lng, lat = v

        if not (-180 <= float(lng) <= 180):
            raise ValueError("invalid longitude")

        if not (-90 <= float(lat) <= 90):
            raise ValueError("invalid latitude")

        return [float(lng), float(lat)]


class DroneHandoffRequest(UpdateLocationRequest):
    order_id: UUID


class DroneHandoffResponse(BaseModel):
    message: str
    order_id: UUID
    old_drone_id: UUID
    new_drone_id: Optional[UUID] = None


class DroneListResponse(BaseModel):
    data: list[DroneBasic]
    meta: Meta
