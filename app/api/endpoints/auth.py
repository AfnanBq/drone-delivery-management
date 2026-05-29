from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.user import UserLogin, UserToken
from app.services.auth import generate_access_token

router = APIRouter()


@router.post("/token", response_model=UserToken)
def create_access_token(
    body: UserLogin,
    db: Session = Depends(get_db),
):
    return generate_access_token(body=body, db=db)
