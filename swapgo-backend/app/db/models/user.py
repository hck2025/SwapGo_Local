from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)  # user | bot | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=kst_now, nullable=False)

    __table_args__ = (Index("ix_users_role", "role"),)
