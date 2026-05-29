from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.crud.user import get_user_by_name_and_role
from app.schemas.user import UserBasic, UserRole

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserBasic:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = get_user_by_name_and_role(db, payload.get("sub"), payload.get("role"))

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    def role_checker(user: UserBasic = Depends(get_current_user)):
        user_role = user.role

        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {allowed_roles}",
            )

        return user

    return role_checker
