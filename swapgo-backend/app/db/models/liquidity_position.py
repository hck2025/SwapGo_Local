from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class LiquidityPosition(Base):
    __tablename__ = "liquidity_positions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "pool_id", name="uq_lp_wallet_pool"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pool_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shares: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, onupdate=kst_now, nullable=False
    )
