from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class AiSignal(Base):
    __tablename__ = "ai_signals"
    __table_args__ = (Index("ix_ai_signal_symbol_time", "symbol", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy | sell | hold
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(64))  # bot:<id>
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
