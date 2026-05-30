from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.drone import DroneBasic, DroneStatus
from app.schemas.order import OrderStatus
from app.schemas.user import UserRole

from .utils import cleanup_records, create_drone, create_order, create_user, get_auth_headers


def test_list_drones_endpoint_returns_registered_drone(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    drone_user = create_user(db, UserRole.DRONE)
    drone = create_drone(db, drone_user.id)

    headers = get_auth_headers(client, admin.name, admin.role)

    try:
        response = client.get("/api/v1/drone/", headers=headers)

        assert response.status_code == 200
        assert any(item["id"] == str(drone.id) and item["user_id"] == drone_user.id for item in response.json())
    finally:
        cleanup_records(db, drone_ids=[drone.id], user_ids=[admin.id, drone_user.id])


def test_update_drone_status_endpoint_updates_database_status(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    drone_user = create_user(db, UserRole.DRONE)
    drone = create_drone(db, drone_user.id, status=DroneStatus.IDLE)

    headers = get_auth_headers(client, admin.name, admin.role)

    try:
        response = client.patch(
            f"/api/v1/drone/{drone.id}?new_status={DroneStatus.BROKEN.value}",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Drone status updated successfully"

        db.refresh(drone)
        assert drone.status == DroneStatus.BROKEN
    finally:
        cleanup_records(db, drone_ids=[drone.id], user_ids=[admin.id, drone_user.id])


def test_update_drone_location_endpoint_updates_coordinates(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    drone = create_drone(db, drone_user.id, status=DroneStatus.IDLE)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    new_location = [39.2, 21.5]

    try:
        response = client.patch(
            "/api/v1/drone/me/location",
            headers=headers,
            json={"location": new_location},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Drone location updated successfully"

        db.refresh(drone)
        drone_in = DroneBasic.model_validate(drone)
        assert new_location == drone_in.location["coordinates"]
    finally:
        cleanup_records(db, drone_ids=[drone.id], user_ids=[drone_user.id])


def test_get_assigned_order_details_endpoint_returns_active_order(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    end_user = create_user(db, UserRole.ENDUSER)
    drone = create_drone(db, drone_user.id, status=DroneStatus.BUSY)
    order = create_order(db, submitted_by_user_id=end_user.id, assigned_drone_id=drone.id, status=OrderStatus.PICKED_UP)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)

    try:
        response = client.get("/api/v1/drone/me/order", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == str(order.id)
        assert response.json()["assigned_drone_id"] == str(drone.id)
    finally:
        cleanup_records(
            db,
            order_ids=[order.id],
            drone_ids=[drone.id],
            user_ids=[drone_user.id, end_user.id],
        )


def test_request_handoff_endpoint_performs_handoff_to_available_drone(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    replacement_drone_user = create_user(db, UserRole.DRONE)
    end_user = create_user(db, UserRole.ENDUSER)
    current_drone = create_drone(db, drone_user.id, status=DroneStatus.BUSY, location=(39.0, 21.0))
    replacement_drone = create_drone(db, user_id=replacement_drone_user.id, status=DroneStatus.IDLE, location=(39.05, 21.05))
    order = create_order(
        db, submitted_by_user_id=end_user.id, assigned_drone_id=current_drone.id, status=OrderStatus.PICKED_UP
    )

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    handoff_payload = {
        "order_id": str(order.id),
        "location": [39.0, 21.0],
    }

    try:
        response = client.post("/api/v1/drone/me/request-handoff", headers=headers, json=handoff_payload)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Order handoff completed successfully"
        assert response_data["order_id"] == str(order.id)
        assert response_data["old_drone_id"] == str(current_drone.id)
        assert response_data["new_drone_id"] == str(replacement_drone.id)

        db.refresh(current_drone)
        db.refresh(replacement_drone)
        db.refresh(order)
        order_status = order.status.value if isinstance(order.status, OrderStatus) else order.status

        assert current_drone.status == DroneStatus.BROKEN
        assert replacement_drone.status == DroneStatus.BUSY
        assert order_status == OrderStatus.HANDOFF_IN_PROGRESS.value
        assert str(order.assigned_drone_id) == response_data["new_drone_id"]
    finally:
        cleanup_records(
            db,
            order_ids=[order.id],
            drone_ids=[current_drone.id, replacement_drone.id],
            user_ids=[drone_user.id, replacement_drone_user.id, end_user.id],
        )


def test_list_drones_endpoint_rejects_non_admin_users(client: TestClient, db: Session):
    end_user = create_user(db, UserRole.ENDUSER)
    headers = get_auth_headers(client, end_user.name, end_user.role)

    try:
        response = client.get("/api/v1/drone/", headers=headers)

        assert response.status_code == 403
        assert response.json()["detail"].startswith("Requires role")
    finally:
        cleanup_records(db, user_ids=[end_user.id])


def test_update_drone_status_endpoint_returns_404_for_missing_drone(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    headers = get_auth_headers(client, admin.name, admin.role)
    missing_id = str(uuid4())

    try:
        response = client.patch(f"/api/v1/drone/{missing_id}?new_status={DroneStatus.BROKEN.value}", headers=headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "Drone not found"
    finally:
        cleanup_records(db, user_ids=[admin.id])


def test_update_drone_location_endpoint_returns_404_for_missing_drone_profile(client: TestClient, db: Session):
    missing_drone_user = create_user(db, UserRole.DRONE)
    headers = get_auth_headers(client, missing_drone_user.name, missing_drone_user.role)

    try:
        response = client.patch(
            "/api/v1/drone/me/location",
            headers=headers,
            json={"location": [39.2, 21.5]},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Drone not found"
    finally:
        cleanup_records(db, user_ids=[missing_drone_user.id])


def test_get_assigned_order_details_endpoint_returns_404_when_no_active_order(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    create_drone(db, drone_user.id, status=DroneStatus.BUSY)
    headers = get_auth_headers(client, drone_user.name, drone_user.role)

    try:
        response = client.get("/api/v1/drone/me/order", headers=headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "No active order assigned"
    finally:
        cleanup_records(db, user_ids=[drone_user.id])


def test_request_handoff_endpoint_rejects_non_busy_drone(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    idle_drone = create_drone(db, drone_user.id, status=DroneStatus.IDLE)
    end_user = create_user(db, UserRole.ENDUSER)
    order = create_order(db, submitted_by_user_id=end_user.id, assigned_drone_id=idle_drone.id, status=OrderStatus.PICKED_UP)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    payload = {"order_id": str(order.id), "location": [39.0, 21.0]}

    try:
        response = client.post("/api/v1/drone/me/request-handoff", headers=headers, json=payload)

        assert response.status_code == 400
        assert response.json()["detail"] == "Drone not eligible to handoff"
    finally:
        cleanup_records(db, order_ids=[order.id], drone_ids=[idle_drone.id], user_ids=[drone_user.id, end_user.id])


def test_request_handoff_endpoint_rejects_order_with_wrong_status(client: TestClient, db: Session):
    drone_user = create_user(db, UserRole.DRONE)
    busy_drone = create_drone(db, drone_user.id, status=DroneStatus.BUSY)
    end_user = create_user(db, UserRole.ENDUSER)
    order = create_order(db, submitted_by_user_id=end_user.id, assigned_drone_id=busy_drone.id, status=OrderStatus.SUBMITTED)

    headers = get_auth_headers(client, drone_user.name, drone_user.role)
    payload = {"order_id": str(order.id), "location": [39.0, 21.0]}

    try:
        response = client.post("/api/v1/drone/me/request-handoff", headers=headers, json=payload)

        assert response.status_code == 400
        assert response.json()["detail"] == "No eligible order found for handoff"
    finally:
        cleanup_records(db, order_ids=[order.id], drone_ids=[busy_drone.id], user_ids=[drone_user.id, end_user.id])
