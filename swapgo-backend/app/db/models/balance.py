from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Balance(Base):
    __tablename__ = "balances"
    __table_args__ = (UniqueConstraint("wallet_id", "asset_symbol", name="uq_balance_wallet_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_symbol: Mapped[str] = mapped_column(
        String(16), ForeignKey("assets.symbol"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
