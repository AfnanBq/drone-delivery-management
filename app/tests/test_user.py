from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.drones import Drones
from app.models.users import Users
from app.schemas.user import UserRole

from .utils import cleanup_records, create_user, get_auth_headers


def test_create_user_endpoint_creates_enduser_for_admin(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    headers = get_auth_headers(client, admin.name, admin.role)
    new_user_name = f"enduser-{uuid4().hex[:8]}"
    payload = {"name": new_user_name, "role": UserRole.ENDUSER.value}

    created_user_id = None
    try:
        response = client.post("/api/v1/user/", headers=headers, json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == new_user_name
        assert body["role"] == UserRole.ENDUSER.value
        created_user_id = int(body["id"])

        user = db.query(Users).filter(Users.id == created_user_id).one_or_none()
        assert user is not None
        assert user.name == new_user_name
        assert user.role == UserRole.ENDUSER
    finally:
        cleanup_records(db, user_ids=[admin.id, created_user_id] if created_user_id else [admin.id])


def test_create_user_endpoint_creates_drone_profile_for_drone_user(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    headers = get_auth_headers(client, admin.name, admin.role)
    new_user_name = f"drone-{uuid4().hex[:8]}"
    payload = {"name": new_user_name, "role": UserRole.DRONE.value}

    created_user_id = None
    created_drone_id = None
    try:
        response = client.post("/api/v1/user/", headers=headers, json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == new_user_name
        assert body["role"] == UserRole.DRONE.value
        created_user_id = int(body["id"])

        drone = db.query(Drones).filter(Drones.user_id == created_user_id).one_or_none()
        assert drone is not None
        created_drone_id = drone.id
    finally:
        cleanup_records(
            db,
            drone_ids=[created_drone_id] if created_drone_id else [],
            user_ids=[admin.id, created_user_id] if created_user_id else [admin.id],
        )


def test_list_users_endpoint_returns_users_for_admin(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    user1 = create_user(db, UserRole.ENDUSER)
    user2 = create_user(db, UserRole.DRONE)
    headers = get_auth_headers(client, admin.name, admin.role)

    try:
        response = client.get("/api/v1/user/", headers=headers)

        assert response.status_code == 200
        returned_names = {item["name"] for item in response.json()}
        assert user1.name in returned_names
        assert user2.name in returned_names
    finally:
        cleanup_records(db, user_ids=[admin.id, user1.id, user2.id])


def test_list_users_endpoint_rejects_non_admin_users(client: TestClient, db: Session):
    end_user = create_user(db, UserRole.ENDUSER)
    headers = get_auth_headers(client, end_user.name, end_user.role)

    try:
        response = client.get("/api/v1/user/", headers=headers)

        assert response.status_code == 403
        assert "Requires role" in response.json()["detail"]
    finally:
        cleanup_records(db, user_ids=[end_user.id])


def test_create_user_endpoint_rejects_duplicate_user(client: TestClient, db: Session):
    admin = create_user(db, UserRole.ADMIN)
    duplicate_name = f"duplicate-user-{uuid4().hex[:8]}"
    existing_user = create_user(db, UserRole.ENDUSER, name=duplicate_name)
    headers = get_auth_headers(client, admin.name, admin.role)
    payload = {"name": existing_user.name, "role": UserRole.ENDUSER.value}

    try:
        response = client.post("/api/v1/user/", headers=headers, json=payload)

        assert response.status_code == 400
        assert response.json()["detail"] == "User already exists"
    finally:
        cleanup_records(db, user_ids=[admin.id, existing_user.id])
