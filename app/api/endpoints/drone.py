from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.schemas import (DroneBasic, DroneHandoffRequest, DroneHandoffResponse, DroneStatus, MessageResponse, OrderBasic,
                         UpdateLocationRequest, UserBasic, UserRole,)
from app.services.drone import (get_drones_service, handoff_order_service, update_drone_location_service,
                                update_drone_status_service,)
from app.services.order import get_assigned_order_details_service

router = APIRouter()


@router.get("/", response_model=List[DroneBasic])
def list_drones(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
):
    return get_drones_service(db=db)


@router.patch("/{drone_id}", response_model=MessageResponse)
def update_drone_status(
    drone_id: UUID,
    new_status: DroneStatus,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    # Mark drones as broken or fixed.
    update_drone_status_service(db=db, drone_id=drone_id, new_status=new_status)
    return MessageResponse(message="Drone status updated successfully")


@router.patch("/me/location", response_model=DroneBasic)
def update_drone_location(
    db: Session = Depends(get_db),
    data: UpdateLocationRequest = Body(...),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN, UserRole.DRONE)),
):
    return update_drone_location_service(db=db, user_id=current_user.id, data=data)


@router.post("/me/request-handoff")
def request_handoff(
    db: Session = Depends(get_db),
    data: DroneHandoffRequest = Body(...),
    current_user: UserBasic = Depends(require_roles(UserRole.DRONE)),
) -> DroneHandoffResponse:
    return handoff_order_service(db=db, user_id=current_user.id, data=data)


@router.get("/me/order", response_model=OrderBasic)
def get_assigned_order_details(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN, UserRole.DRONE)),
):
    return get_assigned_order_details_service(db=db, user_id=current_user.id)
