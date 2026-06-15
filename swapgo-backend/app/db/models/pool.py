from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class Pool(Base):
    __tablename__ = "pools"
    __table_args__ = (UniqueConstraint("base_symbol", "quote_symbol", name="uq_pool_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_symbol: Mapped[str] = mapped_column(String(16), ForeignKey("assets.symbol"), nullable=False)
    quote_symbol: Mapped[str] = mapped_column(String(16), ForeignKey("assets.symbol"), nullable=False)
    reserve_base: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    reserve_quote: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    total_lp_shares: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # quote_id 매칭용
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
