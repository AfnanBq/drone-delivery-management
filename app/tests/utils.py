from uuid import uuid4

from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.crud.user import create_user as create_user_record
from app.models.drones import Drones
from app.models.orders import Orders
from app.models.users import Users
from app.schemas import DroneStatus, OrderStatus, UserCreate, UserRole


def create_user(db: Session, role: UserRole, name: str | None = None) -> Users:
    user_name = name or f"test-{role.value}-{uuid4().hex[:8]}"
    return create_user_record(db=db, data=UserCreate(name=user_name, role=role))


def create_drone(
    db: Session, user_id: int, status: DroneStatus = DroneStatus.IDLE, location: tuple[float, float] = (39.0, 21.0)
) -> Drones:
    point = WKTElement(f"POINT({location[0]} {location[1]})", srid=4326)
    drone = Drones(user_id=user_id, status=status, location=point)
    db.add(drone)
    db.commit()
    db.refresh(drone)
    return drone


def create_order(
    db: Session,
    submitted_by_user_id: int,
    assigned_drone_id: str | None = None,
    status: OrderStatus = OrderStatus.SUBMITTED,
    origin: tuple[float, float] = (39.0, 21.0),
    destination: tuple[float, float] = (39.1, 21.1),
) -> Orders:
    origin_point = WKTElement(f"POINT({origin[0]} {origin[1]})", srid=4326)
    destination_point = WKTElement(f"POINT({destination[0]} {destination[1]})", srid=4326)
    order = Orders(
        status=status,
        origin_location=origin_point,
        destination_location=destination_point,
        assigned_drone_id=assigned_drone_id,
        submitted_by_user_id=submitted_by_user_id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_auth_headers(client: TestClient, name: str, role: UserRole) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        json={"name": name, "role": role},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def cleanup_records(db: Session, *, order_ids=None, drone_ids=None, user_ids=None):
    order_ids = order_ids or []
    drone_ids = drone_ids or []
    user_ids = user_ids or []

    if user_ids:
        user_drone_ids = [drone.id for drone in db.query(Drones).filter(Drones.user_id.in_(user_ids)).all()]
        drone_ids.extend(user_drone_ids)

    drone_ids = list(set(drone_ids))

    order_filters = []
    if order_ids:
        order_filters.append(Orders.id.in_(order_ids))
    if drone_ids:
        order_filters.append(Orders.assigned_drone_id.in_(drone_ids))
    if user_ids:
        order_filters.append(Orders.submitted_by_user_id.in_(user_ids))

    if order_filters:
        db.query(Orders).filter(or_(*order_filters)).delete(synchronize_session=False)
    if drone_ids:
        db.query(Drones).filter(Drones.id.in_(drone_ids)).delete(synchronize_session=False)
    if user_ids:
        db.query(Users).filter(Users.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()
