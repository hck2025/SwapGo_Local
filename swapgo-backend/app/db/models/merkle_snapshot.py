from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class MerkleSnapshot(Base):
    __tablename__ = "merkle_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_tx_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_tx_id: Mapped[int] = mapped_column(Integer, nullable=False)
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
