from typing import Any, Optional
from uuid import UUID

from geoalchemy2 import WKBElement
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.drones import Drones
from app.schemas.drone import DroneStatus


def create_drone(db: Session, drone: Drones):
    try:
        db.add(drone)
        db.commit()
        db.refresh(drone)
        return drone

    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_drones(db: Session):
    try:
        return db.query(Drones).all()
    except SQLAlchemyError as e:
        raise e


def get_drone_by_id(db: Session, drone_id: UUID) -> Drones:
    try:
        return db.query(Drones).filter(Drones.id == drone_id).first()
    except SQLAlchemyError as e:
        raise e


def update_drone_status(db: Session, drone_id: UUID, new_status: DroneStatus) -> None:
    try:
        db.execute(update(Drones).where(Drones.id == drone_id).values(status=new_status))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_drone_by_user_id(db: Session, user_id: int) -> Drones:
    try:
        return db.query(Drones).filter(Drones.user_id == user_id).first()
    except SQLAlchemyError as e:
        raise e


def update_drone(db: Session, obj_in: dict[str, Any], drone_id: UUID) -> None:
    try:
        db.execute(update(Drones).where(Drones.id == drone_id).values(**obj_in))
        db.commit()
    except SQLAlchemyError as e:
        raise e


def get_nearest_available_drone(
    db: Session,
    broken_drone_wkt: WKBElement,
) -> Optional[tuple[Drones, float]]:

    try:
        stmt = (
            select(
                Drones,
                func.ST_Distance(Drones.location, broken_drone_wkt).label("distance"),
            )
            .where(Drones.status == DroneStatus.IDLE)
            .order_by(func.ST_Distance(Drones.location, broken_drone_wkt))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = db.execute(stmt).first()
        return result
    except SQLAlchemyError as e:
        raise e
