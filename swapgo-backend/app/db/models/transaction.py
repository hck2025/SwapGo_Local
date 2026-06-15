from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import kst_now
from app.db.base import Base


class Transaction(Base):
    """체인형 해시 원장. id 자체가 block height. append-only.

    payload_json은 canonical_json 직렬화 가능한 정렬된 JSON. tx_hash 재계산에 사용된다.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_actor_time", "actor_wallet_id", "created_at"),
        Index("ix_tx_pool_time", "pool_id", "created_at"),
        Index("ix_tx_type", "tx_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tx_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_wallet_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("wallets.id", ondelete="SET NULL")
    )
    pool_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pools.id", ondelete="SET NULL"))
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    amount_in: Mapped[int | None] = mapped_column(Numeric(78, 0))
    amount_out: Mapped[int | None] = mapped_column(Numeric(78, 0))
    fee_amount: Mapped[int | None] = mapped_column(Numeric(78, 0))
    slippage_bps: Mapped[int | None] = mapped_column(Integer)
    price_after: Mapped[str | None] = mapped_column(String(64))  # 소수 표현

    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False, index=True
    )
