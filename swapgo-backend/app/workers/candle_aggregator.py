"""1분 단위 캔들 빌더 + 채널 푸시."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.core.time import candle_bucket_start, kst_now
from app.db.base import SessionLocal
from app.db.models.pool import Pool
from app.services import chart_service
from app.services.notifier import hub


async def run_forever(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await _tick()
        except Exception:
            pass
        try:
            # 5초마다 재집계 → 진행 중 캔들이 거의 실시간으로 갱신(프론트 폴링 주기와 일치).
            await asyncio.wait_for(stop_event.wait(), timeout=5)
        except asyncio.TimeoutError:
            continue


# 매 틱마다 갱신할 차트 구간. 진행 중 버킷을 재집계해 캔들이 실시간으로 자란다.
_INTERVALS = ("1m", "5m", "1h", "1d")


async def _tick() -> None:
    now = kst_now()

    db = SessionLocal()
    try:
        pools = list(db.execute(select(Pool).where(Pool.is_active.is_(True))).scalars())
        for p in pools:
            for interval in _INTERVALS:
                # 진행 중 버킷 + 직전 버킷을 재집계(경계에서 직전 버킷 마감 보장).
                # 두 ref 가 같은 버킷이면 set 으로 중복 제거 — 안 그러면 같은
                # (pool,interval,bucket) 을 한 틱에 두 번 INSERT 해 UNIQUE 제약 위반.
                buckets = {
                    candle_bucket_start(now, interval),
                    candle_bucket_start(now - timedelta(seconds=1), interval),
                }
                for bucket in sorted(buckets):
                    candle = chart_service.aggregate_bucket(
                        db, pool_id=p.id, interval=interval, bucket=bucket
                    )
                    if candle is not None:
                        await hub.publish(
                            f"ohlc:{p.id}:{interval}",
                            {
                                "type": "candle",
                                "interval": interval,
                                "bucket_start": candle.bucket_start.isoformat(),
                                "open": candle.open,
                                "high": candle.high,
                                "low": candle.low,
                                "close": candle.close,
                                "volume_base": str(int(candle.volume_base or 0)),
                                "volume_quote": str(int(candle.volume_quote or 0)),
                            },
                        )
        db.commit()
    finally:
        db.close()
