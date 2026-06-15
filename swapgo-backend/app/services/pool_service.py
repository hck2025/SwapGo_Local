"""풀 CRUD 와 가격/뷰 helper."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.amount import to_base_units, to_human
from app.core.errors import DuplicatePool, InvalidAmount, PoolNotFound
from app.db.models.asset import Asset
from app.db.models.pool import Pool
from app.services.amm_engine import initial_lp_shares, pool_price


def list_pools(db: Session, *, only_active: bool = False) -> list[dict]:
    q = select(Pool)
    if only_active:
        q = q.where(Pool.is_active.is_(True))
    rows = list(db.execute(q.order_by(Pool.id.asc())).scalars())
    return [pool_to_dict(db, p) for p in rows]


def get_pool(db: Session, pool_id: int) -> Pool:
    p = db.get(Pool, pool_id)
    if p is None:
        raise PoolNotFound()
    return p


def pool_to_dict(db: Session, p: Pool) -> dict:
    base = db.get(Asset, p.base_symbol)
    quote = db.get(Asset, p.quote_symbol)
    rb = int(p.reserve_base or 0)
    rq = int(p.reserve_quote or 0)
    base_dec = base.decimals if base else 18
    quote_dec = quote.decimals if quote else 18
    raw_price = pool_price(rb, rq)
    # raw_price 는 raw 단위 비율. 사람이 보는 가격(quote per base)은 decimals 보정 필요.
    if rb > 0:
        human_price = raw_price * (10 ** (base_dec - quote_dec))
    else:
        human_price = 0.0
    return {
        "id": p.id,
        "base_symbol": p.base_symbol,
        "quote_symbol": p.quote_symbol,
        "reserve_base": str(rb),
        "reserve_quote": str(rq),
        "reserve_base_human": to_human(rb, base_dec),
        "reserve_quote_human": to_human(rq, quote_dec),
        "price": _fmt(human_price),
        "raw_price": _fmt(raw_price),
        "fee_bps": p.fee_bps,
        "is_active": p.is_active,
        "revision": p.revision,
        "tvl_quote_human": to_human(rq * 2, quote_dec),
    }


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    s = f"{x:.10f}"
    return s.rstrip("0").rstrip(".") or "0"


def create_pool(
    db: Session,
    *,
    base_symbol: str,
    quote_symbol: str,
    init_base_human: str,
    init_quote_human: str,
    fee_bps: int = 30,
) -> dict:
    if base_symbol == quote_symbol:
        raise InvalidAmount("base와 quote 자산은 달라야 해요.")
    base = db.get(Asset, base_symbol)
    quote = db.get(Asset, quote_symbol)
    if base is None or quote is None:
        raise InvalidAmount("등록되지 않은 자산이에요. 먼저 자산을 등록해주세요.")
    existing = db.execute(
        select(Pool).where(Pool.base_symbol == base_symbol, Pool.quote_symbol == quote_symbol)
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicatePool()

    rb = to_base_units(init_base_human, base.decimals)
    rq = to_base_units(init_quote_human, quote.decimals)
    if rb <= 0 or rq <= 0:
        raise InvalidAmount()

    shares = initial_lp_shares(rb, rq)
    pool = Pool(
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        reserve_base=rb,
        reserve_quote=rq,
        total_lp_shares=shares,
        fee_bps=fee_bps,
        is_active=True,
        revision=1,
    )
    db.add(pool)
    db.flush()
    return pool_to_dict(db, pool)
