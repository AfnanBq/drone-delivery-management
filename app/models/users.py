from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas import UserRole


class Users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False)

    __table_args__ = (UniqueConstraint("name", "role", name="uq_user_name_role"),)
