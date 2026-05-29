from fastapi import APIRouter

from app.api.endpoints import auth, drone, order, user

api_router_v1 = APIRouter()
api_router_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router_v1.include_router(user.router, prefix="/user", tags=["user"])
api_router_v1.include_router(drone.router, prefix="/drone", tags=["drone"])
api_router_v1.include_router(order.router, prefix="/order", tags=["order"])
