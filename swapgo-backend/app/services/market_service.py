"""마켓/가격 페이지용 데이터. 거래쌍 단위 통계 + 글로벌 합산."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.amount import to_human
from app.db.models.asset import Asset
from app.db.models.candle import Candle
from app.db.models.pool import Pool
from app.db.models.transaction import Transaction


def list_coins(db: Session) -> list[dict]:
    pools = list(db.execute(select(Pool).where(Pool.is_active.is_(True))).scalars())
    out: list[dict] = []
    for p in pools:
        base = db.get(Asset, p.base_symbol)
        quote = db.get(Asset, p.quote_symbol)
        base_dec = base.decimals if base else 18
        quote_dec = quote.decimals if quote else 18
        rb = int(p.reserve_base or 0)
        rq = int(p.reserve_quote or 0)
        raw_price = (Decimal(rq) / Decimal(rb)) if rb > 0 else Decimal(0)
        # decimals 보정
        scale = Decimal(10) ** (base_dec - quote_dec)
        price = raw_price * scale

        # 24h 변동률 / 거래량 — 1m 캔들 기반
        now = datetime.now(timezone.utc)
        yest = now - timedelta(hours=24)
        candles = list(
            db.execute(
                select(Candle)
                .where(
                    Candle.pool_id == p.id,
                    Candle.interval == "1m",
                    Candle.bucket_start >= yest,
                )
                .order_by(Candle.bucket_start.asc())
            ).scalars()
        )
        if candles:
            first_open = Decimal(candles[0].open)
            change_pct = (
                float((price - first_open) / first_open * 100) if first_open != 0 else 0.0
            )
            vol_q = sum(int(c.volume_quote or 0) for c in candles)
            spark = [float(Decimal(c.close)) for c in candles[-30:]]
        else:
            change_pct = 0.0
            vol_q = 0
            spark = [float(price)] * 5

        out.append(
            {
                "symbol": p.base_symbol,
                "name": base.name if base else p.base_symbol,
                "price_human": _fmt(price),
                "change_24h_pct": round(change_pct, 2),
                "volume_24h_human": str(vol_q),
                "sparkline": spark,
                "pool_id": p.id,
            }
        )
    return out


def global_market(db: Session) -> dict:
    pools = list(db.execute(select(Pool).where(Pool.is_active.is_(True))).scalars())
    total_value_quote = Decimal(0)  # quote 단위(USDT) tvl 합 ≈ 시총 학습용 대용
    btc_value = Decimal(0)
    eth_value = Decimal(0)
    vol_24h = Decimal(0)
    yest = datetime.now(timezone.utc) - timedelta(hours=24)

    for p in pools:
        rb = int(p.reserve_base or 0)
        rq = int(p.reserve_quote or 0)
        tvl = Decimal(rq) * 2  # x*y=k 풀의 TVL 근사: quote_reserve의 2배
        total_value_quote += tvl
        if p.base_symbol.upper() == "BTC":
            btc_value += tvl
        elif p.base_symbol.upper() == "ETH":
            eth_value += tvl
        # 24h 거래량
        candles = list(
            db.execute(
                select(Candle)
                .where(
                    Candle.pool_id == p.id,
                    Candle.interval == "1m",
                    Candle.bucket_start >= yest,
                )
            ).scalars()
        )
        vol_24h += sum(Decimal(c.volume_quote or 0) for c in candles)

    btc_dom = float(btc_value / total_value_quote * 100) if total_value_quote > 0 else 0.0
    eth_dom = float(eth_value / total_value_quote * 100) if total_value_quote > 0 else 0.0

    return {
        "total_market_cap_usdt_human": str(int(total_value_quote)),
        "total_volume_24h_usdt_human": str(int(vol_24h)),
        "btc_dominance_pct": round(btc_dom, 2),
        "eth_dominance_pct": round(eth_dom, 2),
        "note": "이 값들은 거래소 내부 풀 기반 학습용 추정치입니다.",
    }


def recent_trades(db: Session, *, pool_id: int, limit: int = 50) -> list[dict]:
    pool = db.get(Pool, pool_id)
    rows = list(
        db.execute(
            select(Transaction)
            .where(
                Transaction.pool_id == pool_id,
                Transaction.tx_type.in_(("swap", "bot_swap")),
            )
            .order_by(Transaction.id.desc())
            .limit(limit)
        ).scalars()
    )

    _dec_cache: dict[str, int] = {}

    def _dec(symbol: str) -> int:
        if symbol not in _dec_cache:
            a = db.get(Asset, symbol)
            _dec_cache[symbol] = a.decimals if a else 18
        return _dec_cache[symbol]

    base_sym = pool.base_symbol if pool else ""
    out = []
    for r in rows:
        payload = json.loads(r.payload_json)
        side = payload.get("side", "")
        in_sym = payload.get("in_symbol", "")
        out_sym = payload.get("out_symbol", "")
        amt_in = int(r.amount_in or 0)
        amt_out = int(r.amount_out or 0)
        # '수량' 컬럼은 거래된 base 코인 수량으로 통일한다.
        # 매도(base→quote)면 amount_in 이, 매수(quote→base)면 amount_out 이 base.
        base_raw = amt_in if side == "base_to_quote" else amt_out
        out.append(
            {
                "tx_id": r.id,
                "side": side,
                # raw 최소단위(하위호환). 표시는 *_human 을 쓸 것.
                "amount_in": str(amt_in),
                "amount_out": str(amt_out),
                "amount_in_human": to_human(amt_in, _dec(in_sym)) if in_sym else "0",
                "amount_out_human": to_human(amt_out, _dec(out_sym)) if out_sym else "0",
                "amount_base_human": to_human(base_raw, _dec(base_sym)) if base_sym else "0",
                "base_symbol": base_sym,
                "price": r.price_after or "0",
                "slippage_level": _level_for_bps(int(r.slippage_bps or 0)),
                "created_at": r.created_at.isoformat(),
            }
        )
    return out


def _level_for_bps(s: int) -> str:
    if s < 50:
        return "safe"
    if s < 300:
        return "warning"
    return "danger"


def _fmt(d: Decimal) -> str:
    if d == 0:
        return "0"
    s = f"{d:.10f}"
    return s.rstrip("0").rstrip(".") or "0"
