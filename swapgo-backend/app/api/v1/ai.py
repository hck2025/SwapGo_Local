from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db, require_scope
from app.schemas.ai import (
    PredictionsIngestReq,
    SentimentIngestReq,
    SignalsIngestReq,
)
from app.services import ai_ingest_service

router = APIRouter()


@router.get("/signals")
def get_signals(symbol: str | None = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return envelope_ok(ai_ingest_service.list_signals(db, symbol=symbol, limit=limit))


@router.get("/predictions")
def get_predictions(
    symbol: str | None = None,
    horizon: str | None = Query(default=None, pattern="^(1h|24h|7d)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return envelope_ok(
        ai_ingest_service.list_predictions(db, symbol=symbol, horizon=horizon, limit=limit)
    )


@router.get("/sentiment")
def get_sentiment(symbol: str, db: Session = Depends(get_db)):
    return envelope_ok(ai_ingest_service.latest_sentiment(db, symbol=symbol))


@router.post("/ingest/signals", dependencies=[Depends(require_scope("bot:ingest"))])
def ingest_signals(req: SignalsIngestReq, db: Session = Depends(get_db)):
    n = ai_ingest_service.ingest_signals(
        db, source="bot", items=[i.model_dump() for i in req.items]
    )
    return envelope_ok({"inserted": n})


@router.post("/ingest/predictions", dependencies=[Depends(require_scope("bot:ingest"))])
def ingest_predictions(req: PredictionsIngestReq, db: Session = Depends(get_db)):
    n = ai_ingest_service.ingest_predictions(db, items=[i.model_dump() for i in req.items])
    return envelope_ok({"inserted": n})


@router.post("/ingest/sentiment", dependencies=[Depends(require_scope("bot:ingest"))])
def ingest_sentiment(req: SentimentIngestReq, db: Session = Depends(get_db)):
    n = ai_ingest_service.ingest_sentiments(db, items=[i.model_dump() for i in req.items])
    return envelope_ok({"inserted": n})
