from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class AiPrediction(Base):
    __tablename__ = "ai_predictions"
    __table_args__ = (
        Index("ix_ai_pred_symbol_horizon_time", "symbol", "horizon", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon: Mapped[str] = mapped_column(String(8), nullable=False)  # 1h | 24h | 7d
    predicted_price: Mapped[str] = mapped_column(String(64), nullable=False)
    lower_bound: Mapped[str | None] = mapped_column(String(64))
    upper_bound: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_tag: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
