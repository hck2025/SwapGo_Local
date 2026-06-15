from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db
from app.services import chart_service

router = APIRouter()


@router.get("/ohlc")
def ohlc(
    pool_id: int,
    interval: str = Query(default="1m", pattern="^(1m|5m|1h|1d)$"),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    f = datetime.fromisoformat(from_) if from_ else None
    t = datetime.fromisoformat(to) if to else None
    candles = chart_service.list_candles(
        db, pool_id=pool_id, interval=interval, from_ts=f, to_ts=t, limit=limit
    )
    return envelope_ok({"pool_id": pool_id, "interval": interval, "candles": candles})


@router.get("/ticker")
def ticker(pool_id: int, db: Session = Depends(get_db)):
    return envelope_ok(chart_service.ticker_24h(db, pool_id=pool_id))
