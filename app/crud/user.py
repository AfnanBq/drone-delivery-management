import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.users import Users
from app.schemas.user import UserCreate, UserRole

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def create_user(db: Session, data: UserCreate) -> Users:
    try:
        user = Users(**data.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def get_user_by_name_and_role(db: Session, name: str, role: UserRole) -> Users:
    try:
        return db.query(Users).filter(Users.name == name, Users.role == role).first()
    except SQLAlchemyError as e:
        raise e


def get_users(db: Session) -> list[Users]:
    try:
        return db.query(Users).all()
    except SQLAlchemyError as e:
        raise e
