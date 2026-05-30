from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.drone import DroneStatus
from app.schemas.order import OrderStatus
from app.schemas.user import UserRole

from .utils import cleanup_records, create_drone, create_order, create_user, get_auth_headers


def test_submit_order_endpoint_creates_order_for_enduser(client: TestClient, db: Session):
    end_user = create_user(db, UserRole.ENDUSER)
    headers = get_auth_headers(client, end_user.name, end_user.role)
    order_id = None

    payload = {
        "origin_location": [39.0, 21.0],
        "destination_location": [39.1, 21.1],
    }

    try:
        response = client.post("/api/v1/order/", headers=headers, json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["submitted_by_user_id"] == end_user.id
        assert body["status"] == OrderStatus.SUBMITTED.value
        assert body["origin_location"]["coordinates"] == payload["origin_location"]
        assert body["destination_location"]["coordinates"] == payload["destination_location"]
        order_id = body["id"]
    finally:
        cleanup_records(db, order_ids=[order_id] if order_id else [], user_ids=[end_user.id])


def test_list_my_orders_endpoint_returns_user_orders(client: TestClient, db: Session):
    end_user = create_user(db, UserRole.ENDUSER)
    other_user = create_user(db, UserRole.ENDUSER)
    order = create_order(db, submitted_by_user_id=end_user.id)
    other_order = create_order(db, submitted_by_user_id=other_user.id)

    headers = get_auth_headers(client, end_user.name, end_user.role)

    try:
        response = client.get("/api/v1/order/my-orders", headers=headers)

        assert response.status_code == 200
        assert any(item["id"] == str(order.id) for item in response.json())
        assert all(item["submitted_by_user_id"] == end_user.id for item in response.json())
    finally:
        cleanup_records(db, order_ids=[order.id, other_order.id], user_ids=[end_user.id, other_user.id])


def test_list_orders_endpoint_returns_all_orders_for_admin(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    end_user = create_user(db, UserRole.ENDUSER)
    order1 = create_order(db, submitted_by_user_id=end_user.id)
    order2 = create_order(db, submitted_by_user_id=end_user.id)

    headers = get_auth_headers(client, admin.name, admin.role)

    try:
        response = client.get("/api/v1/order/", headers=headers)

        assert response.status_code == 200
        returned_ids = {item["id"] for item in response.json()}
        assert str(order1.id) in returned_ids
        assert str(order2.id) in returned_ids
    finally:
        cleanup_records(db, order_ids=[order1.id, order2.id], user_ids=[admin.id, end_user.id])


def test_change_order_locations_endpoint_updates_locations(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    end_user = create_user(db, UserRole.ENDUSER)
    order = create_order(db, submitted_by_user_id=end_user.id)

    headers = get_auth_headers(client, admin.name, admin.role)
    body = {"origin_location": [39.2, 21.2], "destination_location": [39.3, 21.3]}

    try:
        response = client.patch(f"/api/v1/order/{order.id}/locations", headers=headers, json=body)

        assert response.status_code == 200
        assert response.json()["message"] == "Order locations updated successfully"

        db.refresh(order)
        assert order.origin_location is not None
        assert order.destination_location is not None
    finally:
        cleanup_records(db, order_ids=[order.id], user_ids=[admin.id, end_user.id])


def test_withdraw_order_endpoint_withdraws_user_order(client: TestClient, db: Session):
    end_user = create_user(db, UserRole.ENDUSER)
    order = create_order(db, submitted_by_user_id=end_user.id)

    headers = get_auth_headers(client, end_user.name, end_user.role)

    try:
        response = client.patch(f"/api/v1/order/{order.id}/withdraw", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Order withdrawn successfully"

        db.refresh(order)
        assert order.status == OrderStatus.WITHDRAWN
    finally:
        cleanup_records(db, order_ids=[order.id], user_ids=[end_user.id])


def test_reserve_order_endpoint_assigns_nearest_order_to_drone(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    end_user = create_user(db, UserRole.ENDUSER)
    drone = create_drone(db, user_id=drone_user.id, status=DroneStatus.IDLE)
    order = create_order(db, submitted_by_user_id=end_user.id, status=OrderStatus.SUBMITTED)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)

    try:
        response = client.post("/api/v1/order/reserve", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == str(order.id)
        assert response.json()["assigned_drone_id"] == str(drone.id)
        assert response.json()["status"] == OrderStatus.RESERVED.value

        db.refresh(order)
        assert order.assigned_drone_id == drone.id
        assert order.status == OrderStatus.RESERVED
        db.refresh(drone)
        assert drone.status == DroneStatus.BUSY
    finally:
        cleanup_records(db, order_ids=[order.id], drone_ids=[drone.id], user_ids=[drone_user.id, end_user.id])


def test_update_order_status_endpoint_allows_drone_to_pickup_assigned_order(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    end_user = create_user(db, UserRole.ENDUSER)
    drone = create_drone(db, user_id=drone_user.id, status=DroneStatus.BUSY)
    order = create_order(
        db,
        submitted_by_user_id=end_user.id,
        assigned_drone_id=drone.id,
        status=OrderStatus.RESERVED,
    )

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    payload = {"event": OrderStatus.PICKED_UP.value}

    try:
        response = client.patch(f"/api/v1/order/{order.id}/event", headers=headers, json=payload)

        assert response.status_code == 200

        db.refresh(order)
        assert order.status == OrderStatus.PICKED_UP
    finally:
        cleanup_records(db, order_ids=[order.id], drone_ids=[drone.id], user_ids=[drone_user.id, end_user.id])


def test_update_order_status_endpoint_delivers_assigned_order_after_pickup(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    end_user = create_user(db, UserRole.ENDUSER)
    drone = create_drone(db, user_id=drone_user.id, status=DroneStatus.BUSY)
    order = create_order(
        db,
        submitted_by_user_id=end_user.id,
        assigned_drone_id=drone.id,
        status=OrderStatus.PICKED_UP,
    )

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    payload = {"event": OrderStatus.DELIVERED.value}

    try:
        response = client.patch(f"/api/v1/order/{order.id}/event", headers=headers, json=payload)

        assert response.status_code == 200

        db.refresh(order)
        assert order.status == OrderStatus.DELIVERED
        assert order.delivered_at is not None
    finally:
        cleanup_records(db, order_ids=[order.id], drone_ids=[drone.id], user_ids=[drone_user.id, end_user.id])


def test_reserve_order_endpoint_returns_404_when_no_orders_available(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    drone = create_drone(db, user_id=drone_user.id, status=DroneStatus.IDLE)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)

    try:
        response = client.post("/api/v1/order/reserve", headers=headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "No available orders found"
    finally:
        cleanup_records(db, drone_ids=[drone.id], user_ids=[drone_user.id])
