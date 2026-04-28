from app.models.base import Base
from sqlalchemy.orm import  Mapped, mapped_column
from sqlalchemy import String
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50),unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100),unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)