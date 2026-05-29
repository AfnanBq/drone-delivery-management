import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.crud.drone import (create_drone, get_drone_by_id, get_drone_by_user_id, get_drones, get_nearest_available_drone,
                            update_drone, update_drone_status,)
from app.crud.order import calculate_distance, get_order_by_id, update_order, update_order_status
from app.models import Drones
from app.schemas import DroneBasic, DroneCreate, DroneHandoffRequest, DroneStatus, OrderStatus, UpdateLocationRequest
from app.services.order import DRONE_SPEED

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def create_drone_service(db: Session, user_id: int):
    logger.info("Creating drone with user id=%s", user_id)
    # Create schema object
    drone_data = DroneCreate(user_id=user_id, status=DroneStatus.IDLE)
    # Extract coordinates
    lng, lat = drone_data.location
    # Create PostGIS point
    location_wkt = WKTElement(f"POINT({lng} {lat})", srid=4326)
    db_obj = Drones(user_id=drone_data.user_id, status=drone_data.status, location=location_wkt)
    try:
        create_drone(db=db, drone=db_obj)
    except Exception as e:
        logger.error(f"An error occurred while creating a drone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while while creating a drone",
        )


def get_drones_service(db: Session) -> list[DroneBasic]:
    logger.info("Listing all drones for an admin")
    try:
        drones = [DroneBasic.model_validate(drone) for drone in get_drones(db=db)]
        return drones
    except Exception as e:
        logger.error(f"An error occurred while fetching the drones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the drones",
        )


def update_drone_status_service(drone_id: UUID, new_status: DroneStatus, db: Session) -> None:
    logger.info("Updating drone status for drone=%s", drone_id)
    # check if the drone exists
    drone = get_drone_by_id(db=db, drone_id=drone_id)
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    try:
        # update drone if exists
        update_drone_status(db=db, drone_id=drone_id, new_status=new_status)
    except Exception as e:
        logger.error(f"An error occurred while updating the drone status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the drone status",
        )


def update_drone_location_service(db: Session, user_id: int, data: UpdateLocationRequest) -> None:
    logger.info("Updating drone location for drone user_id=%s", user_id)
    # check if the drone exists
    drone = get_drone_by_user_id(db=db, user_id=user_id)
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    try:
        lng, lat = data.location
        location_wkt = WKTElement(f"POINT({lng} {lat})", srid=4326)
        obj_in = {
            "location": location_wkt,
            "last_heartbeat_at": datetime.now(timezone.utc),
        }
        update_drone(db=db, obj_in=obj_in)
    except Exception as e:
        logger.error(f"An error occurred while updating the drone status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the drone status",
        )


def handoff_order_service(
    db: Session,
    user_id: UUID,
    data: DroneHandoffRequest,
):
    logger.info("Starting handoff for user_id=%s with order=%s", user_id, data.order_id)

    drone = get_drone_by_user_id(db=db, drone_id=user_id)

    if not drone or drone.status != DroneStatus.BUSY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drone not eligible to handoff",
        )
    order = get_order_by_id(db=db, order_id=data.order_id)
    if not order or order.status != OrderStatus.PICKED_UP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No eligible order found for handoff",
        )
    if order.assigned_drone_id != drone.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The drone={drone.id} is not associated to order={data.order_id}",
        )

    try:
        logger.info("Marking drone as BROKEN: drone_id=%s", drone.id)
        # Update drone status + location
        lng, lat = data.location
        location_wkt = WKTElement(f"POINT({lng} {lat})", srid=4326)
        update_drone(
            db=db,
            drone_id=drone.id,
            data={"status": DroneStatus.BROKEN, "location": location_wkt},
        )

        logger.info("Updating order to HANDOFF: order_id=%s", order.id)

        update_order_status(db=db, order_id=order.id, new_status=OrderStatus.HANDOFF_REQUIRED)

        logger.info("Searching for replacement drone for order_id=%s", order.id)

        replacement_drone, handoff_distance = get_nearest_available_drone(
            db=db,
            location=data.location,
        )

        if not replacement_drone:
            logger.error("No available drone found for handoff, order_id=%s", order.id)
            # TODO: Create retry/reassignment background job
            return {
                "message": "No replacement drone available. Order marked for handoff retry.",
                "order_id": str(order.id),
                "old_drone_id": str(drone.id),
                "new_drone_id": None,
            }
        logger.info("Replacement drone found: replacement_drone_id=%s", replacement_drone.id)
        # Resume order
        # Re-compute eta
        remaining_distance = calculate_distance(
            db=db,
            point_a=location_wkt,
            point_b=order.destination_location,
        )

        total_distance = handoff_distance + remaining_distance

        eta = datetime.now(timezone.utc) + timedelta(seconds=total_distance / DRONE_SPEED)
        update_order(
            db=db,
            order_id=order.id,
            data={
                "status": OrderStatus.HANDOFF_IN_PROGRESS,
                "assigned_drone_id": replacement_drone.id,
                "eta": eta,
            },
        )
        # Update replacement drone status
        update_drone(
            db=db,
            drone_id=replacement_drone.id,
            data={
                "status": DroneStatus.BUSY,
            },
        )

        logger.info("Handoff completed successfully for order_id=%s", order.id)

        return {
            "message": "Order handoff completed successfully",
            "order_id": str(order.id),
            "old_drone_id": str(drone.id),
            "new_drone_id": str(replacement_drone.id),
        }

    except Exception as e:
        logger.exception(
            "Handoff failed for drone_id=%s: %s",
            drone.id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during drone handoff",
        )
