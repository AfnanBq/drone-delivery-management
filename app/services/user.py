import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.user import create_user, get_user_by_name_and_role, get_users
from app.schemas import UserBasic, UserCreate, UserListResponse, UserRole
from app.services.drone import create_drone_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def create_user_service(body: UserCreate, db: Session) -> UserBasic:
    logger.info(
        "Creating user request received | name=%s role=%s",
        body.name,
        body.role,
    )
    # check if the user already exists in the db
    name = body.name
    role = body.role
    existing_user = get_user_by_name_and_role(db=db, name=name, role=role)

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    try:
        # create the user in the db
        obj_in = {"name": name, "role": role}
        user = create_user(db=db, data=obj_in)
        logger.info(
            "User created successfully | user_id=%s role=%s",
            user.id,
            user.role,
        )

        if user.role == UserRole.DRONE:
            create_drone_service(db=db, user_id=user.id)
            logger.info(
                "Drone profile created successfully | user_id=%s",
                user.id,
            )

        return UserBasic.model_validate(user)
    except Exception as e:
        logger.error("Unexpected error occurred while creating user | name=%s role=%s. Error: %s", body.name, body.role, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user",
        )


def get_users_service(db: Session, page: int, size: int) -> UserListResponse:
    logger.info("Fetching all users")
    try:
        result = get_users(db, page=page, size=size)
        return UserListResponse(
            data=result["data"],
            meta=result["meta"],
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching the users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the users",
        )
