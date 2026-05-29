import uuid
from datetime import datetime

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.schemas import DroneStatus


class Drones(Base):
    __tablename__ = "drones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    status: Mapped[DroneStatus] = mapped_column(Enum(DroneStatus), nullable=False)

    # PostGIS field
    location: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    last_heartbeat_at: Mapped[datetime | None] = mapped_column(nullable=True)

    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), server_onupdate=func.now(), nullable=False)
