"""유동성 추가/제거. LP 토큰(shares)을 발행/소각한다."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.amount import to_base_units, to_human
from app.core.errors import (
    InsufficientBalance,
    InvalidAmount,
    PoolInactive,
)
from app.core.time import iso_now
from app.db.models.asset import Asset
from app.db.models.balance import Balance
from app.db.models.liquidity_position import LiquidityPosition
from app.db.models.pool import Pool
from app.db.models.wallet import Wallet
from app.services import ledger_service
from app.services.amm_engine import (
    initial_lp_shares,
    quote_add_liquidity_proportional,
    quote_remove_liquidity,
)
from app.services.pool_service import get_pool


def _bal(db: Session, wallet_id: int, symbol: str) -> Balance:
    bal = db.execute(
        select(Balance).where(Balance.wallet_id == wallet_id, Balance.asset_symbol == symbol)
    ).scalar_one_or_none()
    if bal is None:
        bal = Balance(wallet_id=wallet_id, asset_symbol=symbol, amount=0)
        db.add(bal)
        db.flush()
    return bal


def _position(db: Session, wallet_id: int, pool_id: int) -> LiquidityPosition:
    p = db.execute(
        select(LiquidityPosition).where(
            LiquidityPosition.wallet_id == wallet_id,
            LiquidityPosition.pool_id == pool_id,
        )
    ).scalar_one_or_none()
    if p is None:
        p = LiquidityPosition(wallet_id=wallet_id, pool_id=pool_id, shares=0)
        db.add(p)
        db.flush()
    return p


def quote_add(db: Session, *, pool_id: int, base_amount_human: str) -> dict:
    pool = get_pool(db, pool_id)
    base = db.get(Asset, pool.base_symbol)
    quote = db.get(Asset, pool.quote_symbol)
    base_amount = to_base_units(base_amount_human, base.decimals)
    rb = int(pool.reserve_base or 0)
    rq = int(pool.reserve_quote or 0)
    if rb == 0 and rq == 0:
        return {
            "pool_id": pool.id,
            "base_amount": str(base_amount),
            "quote_amount": "0",
            "base_amount_human": to_human(base_amount, base.decimals),
            "quote_amount_human": "0",
            "estimated_shares": "0",
            "is_initial": True,
        }
    quote_amount, shares = quote_add_liquidity_proportional(
        rb, rq, base_amount, total_lp_shares=int(pool.total_lp_shares or 0)
    )
    return {
        "pool_id": pool.id,
        "base_amount": str(base_amount),
        "quote_amount": str(quote_amount),
        "base_amount_human": to_human(base_amount, base.decimals),
        "quote_amount_human": to_human(quote_amount, quote.decimals),
        "estimated_shares": str(shares),
        "is_initial": False,
    }


def add_liquidity(
    db: Session,
    *,
    wallet: Wallet,
    pool_id: int,
    base_amount_human: str,
    quote_amount_human: str,
    min_shares: str = "0",
) -> dict:
    pool = get_pool(db, pool_id)
    if not pool.is_active:
        raise PoolInactive()
    base = db.get(Asset, pool.base_symbol)
    quote = db.get(Asset, pool.quote_symbol)
    base_amount = to_base_units(base_amount_human, base.decimals)
    quote_amount = to_base_units(quote_amount_human, quote.decimals)
    if base_amount <= 0 or quote_amount <= 0:
        raise InvalidAmount()

    rb = int(pool.reserve_base or 0)
    rq = int(pool.reserve_quote or 0)
    total_shares = int(pool.total_lp_shares or 0)

    if rb == 0 and rq == 0:
        shares = initial_lp_shares(base_amount, quote_amount)
    else:
        # 비율이 어긋나면 작은 쪽에 맞춰 사용 (Uniswap V2 스타일)
        adj_quote = (base_amount * rq + rb - 1) // rb
        if adj_quote <= quote_amount:
            quote_amount = adj_quote
        else:
            base_amount = (quote_amount * rb) // rq
        shares = (base_amount * total_shares) // rb

    if shares < int(min_shares):
        raise InvalidAmount("최소 지분 조건을 충족하지 못했어요.")

    base_bal = _bal(db, wallet.id, pool.base_symbol)
    quote_bal = _bal(db, wallet.id, pool.quote_symbol)
    if int(base_bal.amount or 0) < base_amount or int(quote_bal.amount or 0) < quote_amount:
        raise InsufficientBalance()
    base_bal.amount = int(base_bal.amount) - base_amount
    quote_bal.amount = int(quote_bal.amount) - quote_amount

    pool.reserve_base = rb + base_amount
    pool.reserve_quote = rq + quote_amount
    pool.total_lp_shares = total_shares + shares
    pool.revision += 1

    pos = _position(db, wallet.id, pool.id)
    pos.shares = int(pos.shares or 0) + shares

    payload = {
        "actor_address": wallet.address,
        "pool_id": pool.id,
        "base_amount": str(base_amount),
        "quote_amount": str(quote_amount),
        "shares_minted": str(shares),
        "reserve_base_after": str(int(pool.reserve_base)),
        "reserve_quote_after": str(int(pool.reserve_quote)),
        "revision_after": pool.revision,
        "ts": iso_now(),
    }
    tx_type = "bot_add_liq" if _is_bot(db, wallet.id) else "add_liq"
    appended = ledger_service.append_tx(
        db,
        tx_type=tx_type,
        payload=payload,
        actor_wallet_id=wallet.id,
        pool_id=pool.id,
        amount_in=base_amount + quote_amount,
    )
    db.commit()
    return {
        "tx_id": appended.tx_id,
        "tx_hash": appended.tx_hash,
        "shares_delta": str(shares),
        "base_delta": "-" + str(base_amount),
        "quote_delta": "-" + str(quote_amount),
        "pool_after_reserve_base": str(int(pool.reserve_base)),
        "pool_after_reserve_quote": str(int(pool.reserve_quote)),
    }


def remove_liquidity(
    db: Session,
    *,
    wallet: Wallet,
    pool_id: int,
    shares: str,
    min_base: str = "0",
    min_quote: str = "0",
) -> dict:
    pool = get_pool(db, pool_id)
    if not pool.is_active:
        raise PoolInactive()
    shares_i = int(shares)
    pos = _position(db, wallet.id, pool.id)
    if int(pos.shares or 0) < shares_i:
        raise InsufficientBalance()

    rb = int(pool.reserve_base or 0)
    rq = int(pool.reserve_quote or 0)
    total = int(pool.total_lp_shares or 0)
    base_out, quote_out = quote_remove_liquidity(rb, rq, total, shares_i)
    if base_out < int(min_base) or quote_out < int(min_quote):
        raise InvalidAmount("최소 회수 수량을 만족하지 못했어요.")

    pool.reserve_base = rb - base_out
    pool.reserve_quote = rq - quote_out
    pool.total_lp_shares = total - shares_i
    pool.revision += 1
    pos.shares = int(pos.shares) - shares_i

    base_bal = _bal(db, wallet.id, pool.base_symbol)
    quote_bal = _bal(db, wallet.id, pool.quote_symbol)
    base_bal.amount = int(base_bal.amount or 0) + base_out
    quote_bal.amount = int(quote_bal.amount or 0) + quote_out

    payload = {
        "actor_address": wallet.address,
        "pool_id": pool.id,
        "shares_burned": str(shares_i),
        "base_out": str(base_out),
        "quote_out": str(quote_out),
        "reserve_base_after": str(int(pool.reserve_base)),
        "reserve_quote_after": str(int(pool.reserve_quote)),
        "revision_after": pool.revision,
        "ts": iso_now(),
    }
    appended = ledger_service.append_tx(
        db,
        tx_type="remove_liq",
        payload=payload,
        actor_wallet_id=wallet.id,
        pool_id=pool.id,
        amount_out=base_out + quote_out,
    )
    db.commit()
    return {
        "tx_id": appended.tx_id,
        "tx_hash": appended.tx_hash,
        "shares_delta": "-" + str(shares_i),
        "base_delta": str(base_out),
        "quote_delta": str(quote_out),
        "pool_after_reserve_base": str(int(pool.reserve_base)),
        "pool_after_reserve_quote": str(int(pool.reserve_quote)),
    }


def list_positions(db: Session, *, wallet_id: int) -> list[dict]:
    rows = db.execute(
        select(LiquidityPosition, Pool)
        .join(Pool, Pool.id == LiquidityPosition.pool_id)
        .where(LiquidityPosition.wallet_id == wallet_id)
    ).all()
    out: list[dict] = []
    for pos, pool in rows:
        total = int(pool.total_lp_shares or 0)
        my = int(pos.shares or 0)
        pct = (my / total * 100) if total > 0 else 0.0
        out.append(
            {
                "pool_id": pool.id,
                "base_symbol": pool.base_symbol,
                "quote_symbol": pool.quote_symbol,
                "shares": str(my),
                "pool_share_pct": round(pct, 4),
            }
        )
    return out


def _is_bot(db: Session, wallet_id: int) -> bool:
    from app.db.models.user import User
    from app.db.models.wallet import Wallet as W

    w = db.get(W, wallet_id)
    if not w:
        return False
    u = db.get(User, w.user_id)
    return bool(u and u.role == "bot")
