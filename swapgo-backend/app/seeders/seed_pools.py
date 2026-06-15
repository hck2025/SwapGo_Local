"""기본 자산(BTC/ETH/USDT) 등록 + BTC/USDT, ETH/USDT 풀 시드."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.services import pool_service

ASSETS = [
    {"symbol": "USDT", "name": "Tether", "decimals": 6},
    {"symbol": "BTC", "name": "Bitcoin", "decimals": 8},
    {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
]


def run(db: Session) -> None:
    for a in ASSETS:
        if db.get(Asset, a["symbol"]) is None:
            db.add(Asset(**a))
    db.commit()

    # 가격 기준: BTC = 43,250 USDT, ETH = 2,840 USDT
    if not _exists_pool(db, "BTC", "USDT"):
        pool_service.create_pool(
            db,
            base_symbol="BTC",
            quote_symbol="USDT",
            init_base_human="100",  # 100 BTC
            init_quote_human="4325000",  # 4,325,000 USDT
            fee_bps=30,
        )
    if not _exists_pool(db, "ETH", "USDT"):
        pool_service.create_pool(
            db,
            base_symbol="ETH",
            quote_symbol="USDT",
            init_base_human="2000",  # 2,000 ETH
            init_quote_human="5680000",  # 5,680,000 USDT
            fee_bps=30,
        )
    db.commit()


def _exists_pool(db: Session, base: str, quote: str) -> bool:
    from app.db.models.pool import Pool

    return (
        db.execute(
            select(Pool).where(Pool.base_symbol == base, Pool.quote_symbol == quote)
        ).scalar_one_or_none()
        is not None
    )
