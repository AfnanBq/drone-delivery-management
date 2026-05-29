import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import get_user_by_name_and_role
from app.schemas.user import UserLogin

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_access_token(body: UserLogin, db: Session):
    # check user existence in the db
    user = get_user_by_name_and_role(db, body.name, body.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return create_access_token(
        subject=body.name,
        role=body.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
