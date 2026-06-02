from typing import Any, Optional

from sqlalchemy import insert, select
# from app.schemas.shared import Pagination
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.crud.base import paginate
from app.models.users import Users
from app.schemas.user import UserRole


def create_user(db: Session, data: dict[str, Any]) -> Users:
    try:
        result = db.execute(insert(Users).values(data).returning(literal_column("*")))
        db.commit()
        return result.fetchone()
    except (SQLAlchemyError, DBAPIError) as e:
        db.rollback()
        raise Exception(f"Failed to create user: {str(e)}")


def get_user_by_name_and_role(db: Session, name: str, role: UserRole) -> Optional[Users]:
    try:
        return db.execute(select(Users).where(Users.name == name, Users.role == role)).scalar_one_or_none()
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get user with name {name} and {role}: {str(e)}")


def get_users(db: Session, page: int, size: int) -> dict[str, Any]:
    try:
        db_query = select(Users.id, Users.name, Users.role, Users.created_at)
        return paginate(db=db, query=db_query, page=page, size=size)
    except (SQLAlchemyError, DBAPIError) as e:
        raise Exception(f"Failed to get users: {str(e)}")
