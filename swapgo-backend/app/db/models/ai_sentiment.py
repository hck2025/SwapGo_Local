from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class AiSentiment(Base):
    __tablename__ = "ai_sentiments"
    __table_args__ = (Index("ix_ai_sent_symbol_time", "symbol", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_score: Mapped[int] = mapped_column(Integer, nullable=False)  # -100 ~ 100
    rsi: Mapped[float | None] = mapped_column(Float)
    macd: Mapped[float | None] = mapped_column(Float)
    ma7: Mapped[str | None] = mapped_column(String(64))
    ma25: Mapped[str | None] = mapped_column(String(64))
    extra_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
