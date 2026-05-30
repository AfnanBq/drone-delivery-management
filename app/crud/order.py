import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from geoalchemy2 import WKBElement
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.orders import Orders
from app.schemas.order import OrderStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def create_order(db: Session, order: Orders) -> Orders:
    try:
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_orders(db: Session) -> list[Orders]:
    try:
        return db.query(Orders).all()
    except SQLAlchemyError as e:
        raise e


def get_order_by_id(db: Session, order_id: UUID) -> Optional[Orders]:
    try:
        return db.query(Orders).filter(Orders.id == order_id).first()
    except SQLAlchemyError as e:
        raise e


def get_orders_by_user_id(db: Session, user_id: int) -> list[Orders]:
    try:
        return db.query(Orders).filter(Orders.submitted_by_user_id == user_id).all()
    except SQLAlchemyError as e:
        raise e


def update_order_status(
    db: Session,
    order_id: UUID,
    new_status: OrderStatus,
    failure_reason: Optional[str] = None,
) -> None:
    try:
        values = {
            "status": new_status,
        }
        if new_status == OrderStatus.PICKED_UP:
            values["picked_up_at"] = datetime.now(timezone.utc)
        if new_status == OrderStatus.DELIVERED:
            values["delivered_at"] = datetime.now(timezone.utc)
        if new_status == OrderStatus.FAILED:
            values["failure_reason"] = failure_reason
        db.execute(update(Orders).where(Orders.id == order_id).values(**values))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def update_order_location(db: Session, order_id: UUID, data: dict[str, Any]) -> None:
    try:
        db.execute(update(Orders).where(Orders.id == order_id).values(data))
        db.commit()
    except SQLAlchemyError as e:

        db.rollback()
        raise e


def get_nearest_available_order(db: Session, drone_wkt: WKBElement) -> Optional[tuple[Orders, float]]:

    try:
        stmt = (
            select(
                Orders,
                func.ST_Distance(Orders.origin_location, drone_wkt).label("distance"),
            )
            .where(Orders.status == OrderStatus.SUBMITTED)
            .order_by(func.ST_Distance(Orders.origin_location, drone_wkt))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = db.execute(stmt).first()
        return result

    except SQLAlchemyError as e:
        raise e


def update_order(db: Session, order_id: UUID, data: dict[str, Any]) -> None:
    try:
        db.execute(update(Orders).where(Orders.id == order_id).values(**data))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def calculate_distance(db: Session, point_a: WKBElement, point_b: WKBElement) -> float:
    stmt = select(func.ST_DistanceSphere(point_a, point_b))
    distance = db.execute(stmt).scalar()

    return float(distance)


def get_active_order_by_drone_id(db: Session, drone_id: UUID) -> Optional[Orders]:

    active_statuses = [
        OrderStatus.RESERVED,
        OrderStatus.PICKED_UP,
        OrderStatus.HANDOFF_REQUIRED,
        OrderStatus.HANDOFF_IN_PROGRESS,
    ]

    return db.query(Orders).filter(Orders.assigned_drone_id == drone_id, Orders.status.in_(active_statuses)).first()
