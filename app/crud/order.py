from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from geoalchemy2 import WKBElement
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.crud.base import paginate
from app.models.orders import Orders
from app.schemas.order import OrderStatus


def create_order(db: Session, order: dict[str, Any]) -> Orders:
    try:
        result = db.execute(insert(Orders).values(order).returning(literal_column("*")))
        db.commit()
        return result.fetchone()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to create order: {str(e)}")


def get_orders(db: Session, page: int, size: int) -> list[Orders]:
    try:
        query = select(
            Orders.id,
            Orders.submitted_by_user_id,
            Orders.assigned_drone_id,
            Orders.status,
            Orders.origin_location,
            Orders.destination_location,
            Orders.created_at,
            Orders.updated_at,
        )
        return paginate(db=db, query=query, page=page, size=size)
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get orders: {str(e)}")


def get_order_by_id(db: Session, order_id: UUID) -> Optional[Orders]:
    try:
        return db.execute(select(Orders).where(Orders.id == order_id)).scalar_one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get order {order_id}: {str(e)}")


def get_orders_by_user_id(db: Session, user_id: int, page: int, size: int) -> list[Orders]:
    try:
        query = select(
            Orders.id,
            Orders.submitted_by_user_id,
            Orders.assigned_drone_id,
            Orders.status,
            Orders.origin_location,
            Orders.destination_location,
            Orders.created_at,
            Orders.updated_at,
        )
        return paginate(db=db, query=query, page=page, size=size)
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get orders by user {user_id}: {str(e)}")


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
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to update order {order_id} status to {new_status}: {str(e)}")


def update_order_location(db: Session, order_id: UUID, data: dict[str, Any]) -> None:
    try:
        db.execute(update(Orders).where(Orders.id == order_id).values(data))
        db.commit()
    except (SQLAlchemyError, DBAPIError) as e:

        db.rollback()
        raise Exception(f"Failed to update order {order_id} location: {str(e)}")


def get_nearest_available_order(db: Session, drone_wkt: WKBElement) -> Optional[tuple[Orders, float]]:

    try:
        distance = func.ST_Distance(Orders.origin_location, drone_wkt).label("distance")
        stmt = (
            select(
                Orders,
                distance,
            )
            .where(Orders.status == OrderStatus.SUBMITTED)
            .order_by(distance)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = db.execute(stmt).first()
        return result

    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get nearest available order for drone at location {drone_wkt} : {str(e)}")


def update_order(db: Session, order_id: UUID, data: dict[str, Any]) -> None:
    try:
        db.execute(update(Orders).where(Orders.id == order_id).values(**data))
        db.commit()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to update order {order_id} with data {data}: {str(e)}")


def get_active_order_by_drone_id(db: Session, drone_id: UUID) -> Optional[Orders]:

    active_statuses = [
        OrderStatus.RESERVED,
        OrderStatus.PICKED_UP,
        OrderStatus.HANDOFF_REQUIRED,
        OrderStatus.HANDOFF_IN_PROGRESS,
    ]
    try:
        return db.execute(
            select(Orders).where(Orders.assigned_drone_id == drone_id, Orders.status.in_(active_statuses))
        ).scalar_one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get active order for drone {drone_id}: {str(e)}")
