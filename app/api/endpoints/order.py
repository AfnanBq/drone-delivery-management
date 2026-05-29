from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.schemas import (MessageResponse, OrderBasic, OrderCreateRequest, OrderLocationUpdate, OrderStatusUpdateRequest,
                         UserBasic, UserRole,)
from app.services.order import (create_order_service, get_enduser_orders_service, get_orders_service, reserve_order_service,
                                update_order_locations_service, update_order_status_by_drone_service, withdraw_order_service,)

router = APIRouter()


@router.get("/", response_model=List[OrderBasic])
def list_orders(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
):
    return get_orders_service(db=db)


@router.patch("/{order_id}/locations")
def change_order_locations(
    order_id: UUID,
    body: OrderLocationUpdate,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
):

    update_order_locations_service(
        db=db,
        order_id=order_id,
        data=body,
    )
    return MessageResponse(message="Order locations updated successfully")


@router.post("/", response_model=OrderBasic)
def submit_order(
    order: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ENDUSER, UserRole.ADMIN)),
):
    # Submit orders for jobs, with an origin and destination.
    return create_order_service(db=db, body=order, user_id=current_user.id)


@router.get("/my-orders", response_model=List[OrderBasic])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ENDUSER)),
):
    return get_enduser_orders_service(db=db, user_id=current_user.id)


@router.patch("/{order_id}/withdraw", response_model=MessageResponse)
def withdraw_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ENDUSER)),
):
    withdraw_order_service(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
    )
    return MessageResponse(message="Order withdrawn successfully")


@router.post("/reserve", response_model=OrderBasic)
def reserve_order(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.DRONE)),
) -> OrderBasic:
    return reserve_order_service(db=db, user_id=current_user.id)


@router.patch("/{order_id}/event")
def update_order_status_endpoint(
    order_id: UUID,
    data: OrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.DRONE)),
) -> MessageResponse:
    return update_order_status_by_drone_service(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
        data=data,
    )
