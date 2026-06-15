from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        PrimaryKeyConstraint("pool_id", "interval", "bucket_start", name="pk_candle"),
    )

    pool_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pools.id", ondelete="CASCADE"), nullable=False
    )
    interval: Mapped[str] = mapped_column(String(8), nullable=False)  # 1m | 5m | 1h | 1d
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[str] = mapped_column(String(64), nullable=False)
    high: Mapped[str] = mapped_column(String(64), nullable=False)
    low: Mapped[str] = mapped_column(String(64), nullable=False)
    close: Mapped[str] = mapped_column(String(64), nullable=False)
    volume_base: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    volume_quote: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
