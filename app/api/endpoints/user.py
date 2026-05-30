from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.schemas.user import UserBasic, UserCreate, UserRole
from app.services.user import create_user_service, get_users_service

router = APIRouter()


# admin access
@router.get("/", response_model=List[UserBasic])
def list_users(
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
):
    return get_users_service(db=db)


@router.post("/", response_model=UserBasic)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserBasic = Depends(require_roles(UserRole.ADMIN)),
):
    return create_user_service(db=db, body=user)
