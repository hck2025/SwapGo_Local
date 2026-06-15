"""견적+실행. 잔고/풀/tx 갱신을 단일 DB 트랜잭션 안에서 원자 처리."""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.amount import to_base_units, to_human
from app.core.errors import (
    InsufficientBalance,
    InvalidAmount,
    PoolInactive,
    SlippageExceeded,
    StaleQuote,
)
from app.core.time import iso_now, kst_now
from app.db.models.asset import Asset
from app.db.models.balance import Balance
from app.db.models.pool import Pool
from app.db.models.wallet import Wallet
from app.services import ledger_service
from app.services.notifier import publish_sync
from app.services.amm_engine import (
    QuoteResult,
    auto_slippage_tolerance_bps,
    classify_slippage,
    pool_price,
    quote_swap,
)
from app.services.pool_service import get_pool
import logging

logger = logging.getLogger(__name__)


_QUOTE_TTL = timedelta(seconds=15)


def _resolve_in_out(pool: Pool, side: str) -> tuple[str, str, int, int]:
    rb = int(pool.reserve_base or 0)
    rq = int(pool.reserve_quote or 0)
    if side == "base_to_quote":
        return pool.base_symbol, pool.quote_symbol, rb, rq
    if side == "quote_to_base":
        return pool.quote_symbol, pool.base_symbol, rq, rb
    raise InvalidAmount("side는 'base_to_quote' 또는 'quote_to_base' 여야 해요.")


def _price_scale(db: Session, pool: Pool) -> float:
    """raw 준비금 비율(quote/base)을 사람 단위 가격으로 바꾸는 배율.

    사람가격(quote per base) = (rq/rb) * 10^(base_decimals - quote_decimals).
    이 보정이 없으면 ETH(18자리)/USDT(6자리) 풀 가격이 10^12 배 작아져 0원으로 찍힌다.
    chart_service._price_scale / pool_service.pool_to_dict 와 동일 규약.
    """
    base = db.get(Asset, pool.base_symbol)
    quote = db.get(Asset, pool.quote_symbol)
    bdec = base.decimals if base else 18
    qdec = quote.decimals if quote else 18
    return 10.0 ** (bdec - qdec)


def _fmt_price(x: float) -> str:
    if x == 0:
        return "0"
    return f"{x:.10f}".rstrip("0").rstrip(".") or "0"


def _friendly_quote_message(side: str, pool: Pool, q: QuoteResult, level: str) -> str:
    pct = q.amount_in / max(1, q.new_reserve_in - q.amount_in) * 100
    base, quote = pool.base_symbol, pool.quote_symbol
    direction = f"{base}→{quote}" if side == "base_to_quote" else f"{quote}→{base}"
    if level == "danger":
        return (
            f"이 {direction} 거래는 풀 대비 약 {pct:.2f}%로 가격을 크게 움직여요. "
            "수량을 줄이거나 다른 시간대에 다시 시도해보는 걸 권해요."
        )
    if level == "warning":
        return (
            f"이 {direction} 거래로 가격이 약 {q.price_impact_bps/100:.2f}% 움직여요. "
            "허용 슬리피지를 확인해주세요."
        )
    return f"이 {direction} 거래는 가격 영향이 작아요({q.price_impact_bps/100:.2f}%)."


def build_quote(
    db: Session,
    *,
    pool_id: int,
    side: str,
    amount_in_human: str,
    slippage_tolerance_bps: int | None,
) -> dict:
    s = get_settings()
    pool = get_pool(db, pool_id)
    if not pool.is_active:
        raise PoolInactive()
    in_sym, out_sym, r_in, r_out = _resolve_in_out(pool, side)
    in_asset = db.get(Asset, in_sym)
    out_asset = db.get(Asset, out_sym)

    amount_in = to_base_units(amount_in_human, in_asset.decimals)
    q = quote_swap(r_in, r_out, amount_in, fee_bps=pool.fee_bps)

    threshold = (
        slippage_tolerance_bps
        if slippage_tolerance_bps is not None
        else auto_slippage_tolerance_bps(q.price_impact_bps, floor_bps=s.SLIPPAGE_WARN_BPS)
    )
    level = classify_slippage(
        q.slippage_bps,
        warn_bps=s.SLIPPAGE_WARN_BPS,
        danger_bps=s.SLIPPAGE_DANGER_BPS,
    )

    # min_amount_out: amount_out * (1 - threshold)
    amount_out_min = q.amount_out * (10000 - threshold) // 10000

    if side == "base_to_quote":
        new_reserve_base, new_reserve_quote = q.new_reserve_in, q.new_reserve_out
    else:
        new_reserve_base, new_reserve_quote = q.new_reserve_out, q.new_reserve_in
    scale = _price_scale(db, pool)
    new_price = pool_price(new_reserve_base, new_reserve_quote) * scale
    old_price = pool_price(int(pool.reserve_base), int(pool.reserve_quote)) * scale
    # execution_price 는 체결 방향(out/in) 비율이라 방향에 맞춰 보정한다.
    # base_to_quote: quote per base(×scale), quote_to_base: base per quote(×1/scale).
    exec_scale = scale if side == "base_to_quote" else 1.0 / scale

    quote_id = secrets.token_hex(8)
    expires_at = (kst_now() + _QUOTE_TTL).isoformat()

    return {
        "pool_id": pool.id,
        "side": side,
        "amount_in": str(q.amount_in),
        "amount_in_human": to_human(q.amount_in, in_asset.decimals),
        "amount_out": str(q.amount_out),
        "amount_out_human": to_human(q.amount_out, out_asset.decimals),
        "amount_out_min": str(amount_out_min),
        "fee_amount": str(q.fee_amount),
        "fee_bps": q.fee_bps,
        "execution_price": _fmt_price(q.execution_price * exec_scale),
        "mid_price_before": _fmt_price(old_price),
        "mid_price_after": _fmt_price(new_price),
        "price_impact_bps": q.price_impact_bps,
        "slippage_bps": q.slippage_bps,
        "slippage_level": level,
        "slippage_threshold_used_bps": threshold,
        "pool_after": {
            "reserve_base": str(new_reserve_base),
            "reserve_quote": str(new_reserve_quote),
            "price": f"{new_price:.10f}".rstrip("0").rstrip("."),
            "revision": pool.revision + 1,
        },
        "friendly_message": _friendly_quote_message(side, pool, q, level),
        "glossary_keys": _quote_glossary_keys(level),
        "quote_id": quote_id,
        "expires_at": expires_at,
    }


def _quote_glossary_keys(level: str) -> list[str]:
    base = ["slippage", "price_impact", "amm", "cpmm"]
    if level == "danger":
        return base + ["liquidity_pool"]
    return base


def execute_swap(
    db: Session,
    *,
    wallet: Wallet,
    pool_id: int,
    side: str,
    amount_in_human: str,
    min_amount_out: str,
    slippage_tolerance_bps: int,
    expected_revision: int | None = None,
) -> dict:
    logger.info(f"DEBUG_SWAP: amount_in={amount_in_human}, min_out={min_amount_out}")
    pool = get_pool(db, pool_id)
    if not pool.is_active:
        raise PoolInactive()
    if expected_revision is not None and pool.revision > expected_revision:
        # quote 시점 이후 풀이 변경된 경우
        raise StaleQuote()

    in_sym, out_sym, r_in, r_out = _resolve_in_out(pool, side)
    in_asset = db.get(Asset, in_sym)
    out_asset = db.get(Asset, out_sym)
    amount_in = to_base_units(amount_in_human, in_asset.decimals)

    s = get_settings()
    q = quote_swap(r_in, r_out, amount_in, fee_bps=pool.fee_bps)
    min_out = int(min_amount_out)
    logger.error(f"DEBUG_CRITICAL: q.amount_out={q.amount_out}, min_out={min_out}")
    if q.amount_out < min_out:
        raise SlippageExceeded(
            details={"expected_min": str(min_out), "actual": str(q.amount_out)},
        )
    # 추가로 허용 슬리피지 단계도 검사
    if q.slippage_bps > slippage_tolerance_bps:
        raise SlippageExceeded(
            details={
                "tolerance_bps": slippage_tolerance_bps,
                "slippage_bps": q.slippage_bps,
            }
        )

    # 잔고 차감/증가
    in_bal = db.execute(
        select(Balance).where(Balance.wallet_id == wallet.id, Balance.asset_symbol == in_sym)
    ).scalar_one_or_none()
    if in_bal is None or int(in_bal.amount or 0) < amount_in:
        logger.error(f"DEBUG: 잔고 부족! 필요: {amount_in}, 보유: {in_bal.amount if in_bal else 0}")
        raise InsufficientBalance()
    in_bal.amount = int(in_bal.amount) - amount_in

    out_bal = db.execute(
        select(Balance).where(Balance.wallet_id == wallet.id, Balance.asset_symbol == out_sym)
    ).scalar_one_or_none()
    if out_bal is None:
        out_bal = Balance(wallet_id=wallet.id, asset_symbol=out_sym, amount=0)
        db.add(out_bal)
        db.flush()
    out_bal.amount = int(out_bal.amount or 0) + q.amount_out

    # 풀 업데이트
    if side == "base_to_quote":
        pool.reserve_base = q.new_reserve_in
        pool.reserve_quote = q.new_reserve_out
    else:
        pool.reserve_quote = q.new_reserve_in
        pool.reserve_base = q.new_reserve_out
    pool.revision += 1
    scale = _price_scale(db, pool)
    exec_scale = scale if side == "base_to_quote" else 1.0 / scale
    new_price = pool_price(int(pool.reserve_base), int(pool.reserve_quote)) * scale

    is_bot = (db.get(type(wallet), wallet.id) is not None) and getattr(wallet, "_role_bot", False)
    tx_type = "bot_swap" if _wallet_is_bot(db, wallet.id) else "swap"

    payload = {
        "actor_address": wallet.address,
        "pool_id": pool.id,
        "side": side,
        "in_symbol": in_sym,
        "out_symbol": out_sym,
        "amount_in": str(amount_in),
        "amount_out": str(q.amount_out),
        "fee_amount": str(q.fee_amount),
        "fee_bps": q.fee_bps,
        "slippage_bps": q.slippage_bps,
        "price_impact_bps": q.price_impact_bps,
        "reserve_base_after": str(int(pool.reserve_base)),
        "reserve_quote_after": str(int(pool.reserve_quote)),
        "revision_after": pool.revision,
        "ts": iso_now(),
    }
    appended = ledger_service.append_tx(
        db,
        tx_type=tx_type,
        payload=payload,
        actor_wallet_id=wallet.id,
        pool_id=pool.id,
        amount_in=amount_in,
        amount_out=q.amount_out,
        fee_amount=q.fee_amount,
        slippage_bps=q.slippage_bps,
        price_after=f"{new_price:.10f}".rstrip("0").rstrip("."),
    )
    db.commit()

    publish_sync(
        f"trades:{pool.id}",
        {
            "type": "trade",
            "tx_id": appended.tx_id,
            "side": side,
            "amount_in": str(amount_in),
            "amount_out": str(q.amount_out),
            "price": f"{new_price:.10f}".rstrip("0").rstrip("."),
            "slippage_bps": q.slippage_bps,
            "ts": iso_now(),
        },
    )
    publish_sync(
        f"pool:{pool.id}",
        {
            "type": "pool_update",
            "pool_id": pool.id,
            "reserve_base": str(int(pool.reserve_base)),
            "reserve_quote": str(int(pool.reserve_quote)),
            "price": f"{new_price:.10f}".rstrip("0").rstrip("."),
            "revision": pool.revision,
        },
    )

    level = classify_slippage(
        q.slippage_bps,
        warn_bps=s.SLIPPAGE_WARN_BPS,
        danger_bps=s.SLIPPAGE_DANGER_BPS,
    )
    if side == "base_to_quote":
        new_rb, new_rq = q.new_reserve_in, q.new_reserve_out
    else:
        new_rb, new_rq = q.new_reserve_out, q.new_reserve_in

    return {
        "tx_id": appended.tx_id,
        "tx_hash": appended.tx_hash,
        "explorer_url": f"/explorer/tx/{appended.tx_id}",
        "quote": {
            "pool_id": pool.id,
            "side": side,
            "amount_in": str(amount_in),
            "amount_in_human": to_human(amount_in, in_asset.decimals),
            "amount_out": str(q.amount_out),
            "amount_out_human": to_human(q.amount_out, out_asset.decimals),
            "amount_out_min": str(min_out),
            "fee_amount": str(q.fee_amount),
            "fee_bps": q.fee_bps,
            "execution_price": _fmt_price(q.execution_price * exec_scale),
            "mid_price_before": _fmt_price(q.mid_price_before * exec_scale),
            "mid_price_after": _fmt_price(q.mid_price_after * exec_scale),
            "price_impact_bps": q.price_impact_bps,
            "slippage_bps": q.slippage_bps,
            "slippage_level": level,
            "slippage_threshold_used_bps": slippage_tolerance_bps,
            "pool_after": {
                "reserve_base": str(new_rb),
                "reserve_quote": str(new_rq),
                "price": f"{new_price:.10f}".rstrip("0").rstrip("."),
                "revision": pool.revision,
            },
            "friendly_message": _friendly_quote_message(side, pool, q, level),
            "glossary_keys": _quote_glossary_keys(level),
            "quote_id": "executed",
            "expires_at": iso_now(),
        },
    }


def _wallet_is_bot(db: Session, wallet_id: int) -> bool:
    from app.db.models.wallet import Wallet as W
    from app.db.models.user import User

    w = db.get(W, wallet_id)
    if not w:
        return False
    u = db.get(User, w.user_id)
    return bool(u and u.role == "bot")
