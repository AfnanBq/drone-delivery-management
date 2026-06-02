from typing import Any, Optional
from uuid import UUID

from geoalchemy2 import WKBElement
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.crud.base import paginate
from app.models.drones import Drones
from app.schemas import DroneStatus


def create_drone(db: Session, drone: dict[str, Any]) -> Drones:
    try:
        result = db.execute(insert(Drones).values(drone).returning(literal_column("*")))
        db.commit()
        return result.fetchone()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to create drone: {str(e)}")


def get_drones(db: Session, page: int = 1, size: int = 10) -> dict[str, Any]:
    try:
        db_query = select(Drones.id, Drones.user_id, Drones.status, Drones.location, Drones.created_at, Drones.updated_at)
        return paginate(db=db, query=db_query, page=page, size=size)
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get drones: {str(e)}")


def get_drone_by_id(db: Session, drone_id: UUID) -> Optional[Drones]:
    try:
        return db.execute(select(Drones).where(Drones.id == drone_id)).scalar_one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get drone {drone_id}: {str(e)}")


def update_drone_status(db: Session, drone_id: UUID, new_status: DroneStatus) -> None:
    try:
        db.execute(update(Drones).where(Drones.id == drone_id).values(status=new_status))
        db.commit()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to update drone {drone_id}: {str(e)}")


def get_drone_by_user_id(db: Session, user_id: int) -> Optional[Drones]:
    try:
        return db.execute(select(Drones).where(Drones.user_id == user_id)).scalar_one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get drone for user {user_id}: {str(e)}")


def update_drone(db: Session, obj_in: dict[str, Any], drone_id: UUID) -> None:
    try:
        db.execute(update(Drones).where(Drones.id == drone_id).values(**obj_in))
        db.commit()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to update drone {drone_id} with data {obj_in}: {str(e)}")


def get_nearest_available_drone(
    db: Session,
    broken_drone_wkt: WKBElement,
) -> Optional[tuple[Drones, float]]:

    try:
        distance = func.ST_Distance(Drones.location, broken_drone_wkt).label("distance")

        stmt = (
            select(Drones, distance)
            .where(Drones.status == DroneStatus.IDLE)
            .order_by(distance)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return db.execute(stmt).one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to find the nearest available drone: {str(e)}")
