"""OHLC 캔들 집계.

Phase A 단계에서는 트랜잭션을 그때그때 집계하는 단순 빌더로 충분.
Phase D에서 워커가 1분마다 candles 테이블을 upsert 하도록 한다.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.time import candle_bucket_start, interval_seconds
from app.db.models.asset import Asset
from app.db.models.candle import Candle
from app.db.models.pool import Pool
from app.db.models.transaction import Transaction


def _price_scale(db: Session, pool: Pool) -> Decimal:
    """raw 준비금 비율(quote/base)을 사람 단위 가격으로 바꾸는 배율.

    가격(사람) = (rq/10^qdec) / (rb/10^bdec) = (rq/rb) * 10^(bdec-qdec).
    예) BTC(8)/USDT(6) → 10^(8-6)=100 배. 이 보정이 없으면 시드 캔들(~43,250)과
    실시간 캔들(~432)의 스케일이 100배 어긋나 차트가 절벽처럼 폭락한다.
    """
    base = db.get(Asset, pool.base_symbol)
    quote = db.get(Asset, pool.quote_symbol)
    bdec = base.decimals if base else 18
    qdec = quote.decimals if quote else 18
    return Decimal(10) ** (bdec - qdec)


def _swap_price_from_payload(payload: dict, pool: Pool, scale: Decimal) -> Decimal | None:
    rb = payload.get("reserve_base_after")
    rq = payload.get("reserve_quote_after")
    if rb is None or rq is None:
        return None
    rb_d = Decimal(rb)
    rq_d = Decimal(rq)
    if rb_d == 0:
        return None
    return (rq_d / rb_d) * scale


def list_candles(
    db: Session,
    *,
    pool_id: int,
    interval: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    q = select(Candle).where(Candle.pool_id == pool_id, Candle.interval == interval)
    if from_ts is not None:
        q = q.where(Candle.bucket_start >= from_ts)
    if to_ts is not None:
        q = q.where(Candle.bucket_start <= to_ts)
    # 최신 limit 개를 가져와야 한다. ASC+limit 이면 캔들이 limit 을 넘는 순간
    # '가장 오래된' limit 개만 나와 실시간 캔들이 잘려 차트가 과거에 멈춘다.
    # DESC 로 최신부터 limit 개를 뽑은 뒤, 표시용으로 시간 오름차순으로 되돌린다.
    q = q.order_by(Candle.bucket_start.desc()).limit(limit)
    rows = list(reversed(list(db.execute(q).scalars())))
    return [
        {
            "bucket_start": r.bucket_start.isoformat(),
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume_base": str(int(r.volume_base or 0)),
            "volume_quote": str(int(r.volume_quote or 0)),
            "trades_count": r.trades_count,
        }
        for r in rows
    ]


def aggregate_minute(db: Session, *, pool_id: int, bucket: datetime) -> Candle | None:
    """하위호환 별칭 — 1m 버킷 집계."""
    return aggregate_bucket(db, pool_id=pool_id, interval="1m", bucket=bucket)


def aggregate_bucket(
    db: Session, *, pool_id: int, interval: str, bucket: datetime
) -> Candle | None:
    """bucket(해당 interval) 동안의 swap 트랜잭션을 모아 캔들을 upsert.

    1m 뿐 아니라 5m/1h/1d 도 같은 로직으로 집계해 모든 차트 구간이 실시간 갱신되게 한다.
    """
    pool = db.get(Pool, pool_id)
    if pool is None:
        return None
    next_bucket = bucket + timedelta(seconds=interval_seconds(interval))

    rows = list(
        db.execute(
            select(Transaction)
            .where(
                Transaction.pool_id == pool_id,
                Transaction.tx_type.in_(("swap", "bot_swap")),
                Transaction.created_at >= bucket,
                Transaction.created_at < next_bucket,
            )
            .order_by(Transaction.id.asc())
        ).scalars()
    )

    candle = db.execute(
        select(Candle).where(
            Candle.pool_id == pool_id,
            Candle.interval == interval,
            Candle.bucket_start == bucket,
        )
    ).scalar_one_or_none()

    if not rows:
        # 거래가 없으면 직전 close 로 평탄화
        prev = db.execute(
            select(Candle)
            .where(
                Candle.pool_id == pool_id,
                Candle.interval == interval,
                Candle.bucket_start < bucket,
            )
            .order_by(Candle.bucket_start.desc())
            .limit(1)
        ).scalar_one_or_none()
        if prev is None:
            return None
        flat = prev.close
        if candle is None:
            candle = Candle(
                pool_id=pool_id,
                interval=interval,
                bucket_start=bucket,
                open=flat,
                high=flat,
                low=flat,
                close=flat,
                volume_base=0,
                volume_quote=0,
                trades_count=0,
            )
            db.add(candle)
        return candle

    scale = _price_scale(db, pool)
    prices: list[Decimal] = []
    vol_base = 0
    vol_quote = 0
    for r in rows:
        payload = json.loads(r.payload_json)
        price = _swap_price_from_payload(payload, pool, scale)
        if price is None:
            continue
        prices.append(price)
        in_sym = payload.get("in_symbol")
        amt_in = int(payload.get("amount_in", 0))
        amt_out = int(payload.get("amount_out", 0))
        if in_sym == pool.base_symbol:
            vol_base += amt_in
            vol_quote += amt_out
        else:
            vol_quote += amt_in
            vol_base += amt_out

    if not prices:
        return None
    # 6자리로 양자화해 저장(시드 캔들과 동일 포맷). 양자화 없이 str(Decimal) 하면
    # 준비금 나눗셈의 80자리 가까운 무한소수가 그대로 직렬화돼 차트/툴팁이 지저분해진다.
    o = _q(prices[0])
    c = _q(prices[-1])
    h = _q(max(prices))
    l = _q(min(prices))

    if candle is None:
        candle = Candle(
            pool_id=pool_id,
            interval=interval,
            bucket_start=bucket,
            open=o,
            high=h,
            low=l,
            close=c,
            volume_base=vol_base,
            volume_quote=vol_quote,
            trades_count=len(rows),
        )
        db.add(candle)
    else:
        candle.open = o
        candle.high = h
        candle.low = l
        candle.close = c
        candle.volume_base = vol_base
        candle.volume_quote = vol_quote
        candle.trades_count = len(rows)
    return candle


def ticker_24h(db: Session, *, pool_id: int) -> dict:
    pool = db.get(Pool, pool_id)
    if pool is None:
        return {}
    now = datetime.now(timezone.utc)
    yest = now - timedelta(hours=24)
    bucket = candle_bucket_start(yest, "1m")

    rows = list(
        db.execute(
            select(Candle)
            .where(
                Candle.pool_id == pool_id,
                Candle.interval == "1m",
                Candle.bucket_start >= bucket,
            )
            .order_by(Candle.bucket_start.asc())
        ).scalars()
    )

    rb = int(pool.reserve_base or 0)
    rq = int(pool.reserve_quote or 0)
    scale = _price_scale(db, pool)
    last_price = (Decimal(rq) / Decimal(rb) * scale) if rb > 0 else Decimal(0)

    if rows:
        first_open = Decimal(rows[0].open)
        high = max(Decimal(r.high) for r in rows)
        low = min(Decimal(r.low) for r in rows)
        vol_b = sum(int(r.volume_base or 0) for r in rows)
        vol_q = sum(int(r.volume_quote or 0) for r in rows)
        change_pct = (
            float((last_price - first_open) / first_open * 100) if first_open != 0 else 0.0
        )
    else:
        first_open = last_price
        high = last_price
        low = last_price
        vol_b = 0
        vol_q = 0
        change_pct = 0.0

    return {
        "pool_id": pool_id,
        "last_price": _fmt(last_price),
        "high_24h": _fmt(high),
        "low_24h": _fmt(low),
        "change_24h_pct": round(change_pct, 4),
        "volume_24h_base": str(vol_b),
        "volume_24h_quote": str(vol_q),
    }


def _q(d: Decimal) -> str:
    """가격 Decimal 을 6자리 사람 단위 문자열로 양자화."""
    return f"{d:.6f}"


def _fmt(d: Decimal) -> str:
    s = f"{d:.10f}"
    return s.rstrip("0").rstrip(".") or "0"
