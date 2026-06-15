"""데모 상태 리셋: 풀 준비금을 시드 초기값으로 되돌리고, 캔들/스왑 트랜잭션을
깨끗이 지운 뒤 1m/5m/1h/1d 캔들을 일관된 가격대로 재시드한다.

가격 단위 버그(준비금 raw 비율을 그대로 가격으로 쓰던 문제) 수정 이전에 잘못 기록된
~500 스케일 캔들과, 테스트 거래로 흐트러진 풀 상태를 한 번에 정리하기 위한 일회성 도구.

백엔드 venv 에서 실행:  python reset_demo.py
봇/유저/API 키는 건드리지 않으므로 엔진 .env 의 봇 키는 그대로 유효하다.
"""

from __future__ import annotations

import math
from datetime import timedelta

from app.core.time import candle_bucket_start, kst_now
from app.db.base import SessionLocal, init_schema
from app.db.models.asset import Asset
from app.db.models.candle import Candle
from app.db.models.pool import Pool
from app.services import ledger_service

# 시드 초기 준비금(seed_pools 와 동일) — 사람 가격: BTC=43,250 / ETH=2,840
POOL_INIT = {
    1: {"base": "BTC", "quote": "USDT", "rb_human": 100, "rq_human": 4_325_000},
    2: {"base": "ETH", "quote": "USDT", "rb_human": 2_000, "rq_human": 5_680_000},
}

N = 200  # 구간별 시드 캔들 개수
INTERVALS = (("1m", 1), ("5m", 5), ("1h", 60), ("1d", 1440))


def _to_base_units(db, symbol: str, human: float) -> int:
    asset = db.get(Asset, symbol)
    dec = asset.decimals if asset else 18
    return int(round(human * (10 ** dec)))


def _walk(base: float, i: int, amp: float, period: float) -> float:
    return base * (1 + amp * math.sin(i / period) + 0.0005 * ((i * 37) % 11 - 5))


def reset_pool_reserves(db) -> dict[int, float]:
    """풀 준비금을 초기값으로 되돌리고 사람 가격을 반환."""
    prices: dict[int, float] = {}
    for pid, cfg in POOL_INIT.items():
        pool = db.get(Pool, pid)
        if pool is None:
            continue
        rb = _to_base_units(db, cfg["base"], cfg["rb_human"])
        rq = _to_base_units(db, cfg["quote"], cfg["rq_human"])
        pool.reserve_base = rb
        pool.reserve_quote = rq
        pool.revision = (pool.revision or 0) + 1
        prices[pid] = cfg["rq_human"] / cfg["rb_human"]
    db.commit()
    return prices


def seed_candles(db, pool_id: int, base_price: float, vol_unit: int) -> None:
    """마지막 캔들 close 가 현재 풀 가격(base_price)에 수렴하도록 결정적 walk 시드."""
    now = kst_now()
    for interval, step_min in INTERVALS:
        step = timedelta(minutes=step_min)
        # 버킷을 interval 경계에 정렬 → 라이브 aggregator(:00 정렬)와 이음새가 맞는다.
        # 마지막 시드 버킷 = aligned_now - step, 현재 라이브 버킷 = aligned_now.
        aligned_now = candle_bucket_start(now, interval)
        start = aligned_now - step * N
        for i in range(N):
            bucket = start + step * i
            c = _walk(base_price, i, 0.03, 17)
            o = _walk(base_price, i - 1, 0.03, 17)
            hi = max(o, c) * 1.001
            lo = min(o, c) * 0.999
            db.add(Candle(
                pool_id=pool_id, interval=interval, bucket_start=bucket,
                open=f"{o:.6f}", high=f"{hi:.6f}", low=f"{lo:.6f}", close=f"{c:.6f}",
                volume_base=int(vol_unit * (1 + (i % 7) * 0.1)),
                volume_quote=int(vol_unit * c * (1 + (i % 7) * 0.1)),
                trades_count=5 + (i % 9),
            ))
    db.commit()


def main() -> None:
    init_schema()
    with SessionLocal() as db:
        prices = reset_pool_reserves(db)
        print(f"[reset] 풀 준비금 초기화 완료 가격={prices}")

        # 캔들만 비우고 재시드한다. 트랜잭션 원장은 절대 삭제하지 않는다 —
        # 중간 삭제는 prev_hash→tx_hash 해시 체인을 끊어 /explorer/verify 가
        # 무결성 위반으로 잡는다(원장은 append-only 설계). 24h ticker/거래량은
        # 캔들에서 계산하므로 트랜잭션을 지울 필요도 없다.
        deleted_c = db.query(Candle).delete()
        db.commit()
        print(f"[reset] 캔들 {deleted_c}개 삭제 (트랜잭션 원장은 보존)")

        # 과거 리셋 등으로 끊겼을 수 있는 해시 체인을 genesis 부터 재계산해 복구.
        repair = ledger_service.rechain_ledger(db)
        print(
            f"[reset] 원장 체인 복구: {repair['rechained']}건 재계산, "
            f"머클 스냅샷 {repair['merkle_snapshots_cleared']}개 정리"
        )

        seed_candles(db, 1, prices.get(1, 43250.0), 100_000_000)
        seed_candles(db, 2, prices.get(2, 2840.0), 1_000_000_000)
        total = db.query(Candle).count()
        print(f"[reset] 캔들 재시드 완료 total={total} (풀2개 x 4구간 x {N})")


if __name__ == "__main__":
    main()
