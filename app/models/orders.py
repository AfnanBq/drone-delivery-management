import uuid
from typing import Optional

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.schemas import OrderStatus


class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[OrderStatus] = mapped_column(String(20), nullable=False)
    origin_location: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination_location: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    assigned_drone_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("drones.id"), nullable=True)
    submitted_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    eta: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    picked_up_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)

    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
