import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.crud.drone import get_drone_by_user_id, update_drone_status
from app.crud.order import (create_order, get_active_order_by_drone_id, get_nearest_available_order, get_order_by_id,
                            get_orders, get_orders_by_user_id, update_order, update_order_location, update_order_status,)
from app.schemas import (OrderBasic, OrderCreate, OrderCreateRequest, OrderListResponse, OrderLocationUpdate, OrderStatus,
                         OrderStatusUpdateRequest,)
from app.schemas.drone import DroneStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)

DRONE_SPEED = 12  # meters per second - assume all drones have the same value


def create_order_service(db: Session, body: OrderCreateRequest, user_id: int) -> OrderBasic:
    """Create order without assigned drone."""
    logger.info(
        "Create order request received | user_id=%s",
        user_id,
    )
    # Prevent same origin/destination
    if body.origin_location == body.destination_location:
        logger.warning(
            "Order creation failed: origin and destination are identical | user_id=%s",
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Origin and destination cannot be the same",
        )

    try:
        logger.info(
            "Building order payload | user_id=%s",
            user_id,
        )
        # Build internal schema
        order_data = OrderCreate(
            **body.model_dump(),
            submitted_by_user_id=user_id,
        )

        # Extract coordinates
        origin_lng, origin_lat = order_data.origin_location
        destination_lng, destination_lat = order_data.destination_location

        logger.info(
            "Parsed coordinates successfully | user_id=%s " "origin=(%s,%s) destination=(%s,%s)",
            user_id,
            origin_lat,
            origin_lng,
            destination_lat,
            destination_lng,
        )

        # Convert to PostGIS POINT
        origin_wkt = WKTElement(
            f"POINT({origin_lng} {origin_lat})",
            srid=4326,
        )

        destination_wkt = WKTElement(
            f"POINT({destination_lng} {destination_lat})",
            srid=4326,
        )
        logger.info(
            "Converted coordinates to PostGIS points | user_id=%s",
            user_id,
        )
        # Create db object
        db_obj = {
            "status": order_data.status,
            "submitted_by_user_id": order_data.submitted_by_user_id,
            "origin_location": origin_wkt,
            "destination_location": destination_wkt,
        }
        order = create_order(db=db, order=db_obj)
        logger.info(
            "Order created successfully | order_id=%s user_id=%s status=%s",
            order.id,
            user_id,
            order.status,
        )
        return OrderBasic.model_validate(order)
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order",
        )


def get_orders_service(db: Session, page: int, size: int) -> list[OrderBasic]:
    try:
        logger.info("Fetching all orders")
        result = get_orders(db=db, page=page, size=size)
        return OrderListResponse(data=result["data"], meta=result["meta"])
    except Exception as e:
        logger.error(f"An error occurred while fetching the orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the orders",
        )


def get_enduser_orders_service(db: Session, user_id: int, page: int, size: int) -> list[OrderBasic]:
    try:
        logger.info(
            "Fetching all orders for user=%s",
            user_id,
        )
        result = get_orders_by_user_id(db=db, user_id=user_id, page=page, size=size)
        return OrderListResponse(data=result["data"], meta=result["meta"])
    except Exception as e:
        logger.error(f"An error occurred while fetching the orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the orders",
        )


def withdraw_order_service(db: Session, order_id: UUID, user_id: int) -> None:
    logger.info(
        "Withdraw order request received | order_id=%s user_id=%s",
        order_id,
        user_id,
    )
    order = get_order_by_id(db=db, order_id=order_id)
    if not order:
        logger.warning(
            "Order withdrawal failed: order not found | order_id=%s user_id=%s",
            order_id,
            user_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.submitted_by_user_id != user_id:
        logger.warning(
            "Unauthorized withdrawal attempt | order_id=%s owner_id=%s requester_id=%s",
            order_id,
            order.submitted_by_user_id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to withdraw this order",
        )
    if order.status not in [OrderStatus.SUBMITTED, OrderStatus.RESERVED]:
        logger.warning(
            "Invalid order status for withdrawal | order_id=%s status=%s",
            order_id,
            order.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only orders with status 'SUBMITTED' or 'RESERVED' can be withdrawn",
        )
    try:
        update_order_status(db=db, order_id=order_id, new_status=OrderStatus.WITHDRAWN)
        logger.info(
            "Order withdrawn successfully | order_id=%s user_id=%s",
            order_id,
            user_id,
        )
    except Exception as e:
        logger.error(
            "Unexpected error occurred while withdrawing order | order_id=%s user_id=%s. Error: %s", order_id, user_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while withdrawing the order",
        )


def update_order_locations_service(
    db: Session,
    order_id: UUID,
    data: OrderLocationUpdate,
) -> None:
    logger.info(
        "Updating order locations | order_id=%s, origin=%s, destination=%s",
        order_id,
        data.origin_location,
        data.destination_location,
    )
    order = get_order_by_id(db=db, order_id=order_id)
    if not order:
        logger.warning("Order not found: order_id=%s", order_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status not in [
        OrderStatus.SUBMITTED,
        OrderStatus.RESERVED,
    ]:
        logger.warning(
            "Invalid order status for location update: order_id=%s, status=%s",
            order_id,
            order.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only orders with status 'SUBMITTED' or 'RESERVED' can have their locations updated",
        )

    # Determine new/fallback coordinates
    origin_point = to_shape(order.origin_location)
    origin = data.origin_location if data.origin_location else [origin_point.x, origin_point.y]

    destination_point = to_shape(order.destination_location)
    destination = data.destination_location if data.destination_location else [destination_point.x, destination_point.y]
    # validate origin shouldn't equal the destination
    if origin == destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Origin and destination cannot be the same",
        )
    try:
        # Prepare DB update dictionary
        update_data = {}
        if data.origin_location:
            lng, lat = data.origin_location
            update_data["origin_location"] = WKTElement(f"POINT({lng} {lat})", srid=4326)

        if data.destination_location:
            lng, lat = data.destination_location
            update_data["destination_location"] = WKTElement(f"POINT({lng} {lat})", srid=4326)

        # Perform DB update
        update_order_location(
            db=db,
            order_id=order_id,
            data=update_data,
        )

        logger.info("Order with ID =%s locations updated successfully", order_id)

    except Exception as e:
        logger.error(f"Error updating order locations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the order locations",
        )


def reserve_order_service(db: Session, user_id: int) -> OrderBasic:
    logger.info("Reserving order for drone with user_id=%s", user_id)
    drone = get_drone_by_user_id(db=db, user_id=user_id)
    if drone.status != DroneStatus.IDLE:
        raise HTTPException(
            status_code=400,
            detail="Drone must be IDLE to reserve an order",
        )
    # Get drone location (stored as PostGIS)
    drone_point = to_shape(drone.location)
    drone_wkt = WKTElement(
        f"POINT({drone_point.x} {drone_point.y})",
        srid=4326,
    )

    # Find nearest available order using PostGIS
    nearest_result = get_nearest_available_order(db=db, drone_wkt=drone_wkt)
    if not nearest_result:
        raise HTTPException(
            status_code=404,
            detail="No available orders found",
        )

    nearest_order, distance = nearest_result
    try:
        # compute eta
        eta = datetime.now(timezone.utc) + timedelta(seconds=distance / DRONE_SPEED)
        # Assign drone + update order
        data = {
            "assigned_drone_id": drone.id,
            "eta": eta,
            "status": OrderStatus.RESERVED,
        }
        update_order(db=db, order_id=nearest_order.id, data=data)
        db.refresh(nearest_order)
        # Update drone status
        update_drone_status(db=db, drone_id=drone.id, new_status=DroneStatus.BUSY)

        # Return response
        return OrderBasic.model_validate(nearest_order)
    except Exception as e:
        logger.error(f"Error reserving order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while reserving an order",
        )


def update_order_status_by_drone_service(
    db: Session,
    order_id: UUID,
    user_id: int,
    data: OrderStatusUpdateRequest,
) -> None:
    logger.info("Updating order=%s status by user=%s", order_id, user_id)
    drone = get_drone_by_user_id(db=db, user_id=user_id)
    order = get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    # Ensure drone owns order
    if not drone or order.assigned_drone_id != drone.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drone not assigned to this order",
        )

    # Validate transitions
    allowed_transitions = {
        OrderStatus.RESERVED: [OrderStatus.PICKED_UP],
        OrderStatus.PICKED_UP: [OrderStatus.DELIVERED, OrderStatus.FAILED],
    }

    if order.status not in allowed_transitions:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid order state")

    new_status = OrderStatus(data.event.value)

    if new_status not in allowed_transitions[order.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status} to {new_status}",
        )
    try:
        # Update DB
        update_order_status(
            db=db,
            order_id=order.id,
            new_status=new_status,
            failure_reason=data.failure_reason,
        )
    except Exception as e:
        logger.error(f"Error updating order status by drone {drone.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the order status",
        )


def get_assigned_order_details_service(
    db: Session,
    user_id: int,
) -> OrderBasic:
    logger.info(
        "Fetching assigned order for drone user_id=%s",
        user_id,
    )

    drone = get_drone_by_user_id(db=db, user_id=user_id)

    if not drone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drone profile not found",
        )
    order = get_active_order_by_drone_id(
        db=db,
        drone_id=drone.id,
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active order assigned",
        )

    logger.info(
        "Assigned order retrieved successfully: order_id=%s",
        order.id,
    )
    return OrderBasic.model_validate(order)
