"""통합테스트용 합성 캔들 시더 (1m + 5m, pool 1/2).
빈 DB에서 차트와 AI ingest 파이프라인이 살아나도록 결정적 walk 로 채운다.
백엔드 venv 에서 실행."""
import math
from datetime import timedelta

from app.db.base import SessionLocal, init_schema
from app.db.models.candle import Candle
from app.core.time import kst_now

init_schema()

N = 200


def walk(base, i, amp, period):
    return base * (1 + amp * math.sin(i / period) + 0.0005 * ((i * 37) % 11 - 5))


def seed(db, pool_id, base_price, vol_unit, interval, step_min):
    now = kst_now()
    step = timedelta(minutes=step_min)
    start = now - step * N
    for i in range(N):
        bucket = start + step * i
        c = walk(base_price, i, 0.03, 17)
        o = walk(base_price, i - 1, 0.03, 17)
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


with SessionLocal() as db:
    for iv, step in (("1m", 1), ("5m", 5)):
        db.query(Candle).filter(Candle.interval == iv).delete()
        db.commit()
        seed(db, 1, 43000.0, 100_000_000, iv, step)
        seed(db, 2, 2900.0, 1_000_000_000, iv, step)
    total = db.query(Candle).count()
    print(f"seeded candles total={total} (pool1/2 x 1m/5m x {N})")
