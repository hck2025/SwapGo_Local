"""AI팀 봇이 업로드하는 시그널/예측/심리 데이터 수집과 조회."""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.amount import to_base_units, to_human
from app.core.time import kst_now
from app.db.models.ai_prediction import AiPrediction
from app.db.models.ai_sentiment import AiSentiment
from app.db.models.ai_signal import AiSignal
from app.db.models.asset import Asset


def ingest_signals(db: Session, *, source: str, items: list[dict]) -> int:
    n = 0
    now = kst_now()
    for it in items:
        expires_at = (
            now + timedelta(seconds=int(it["expires_in_sec"]))
            if it.get("expires_in_sec")
            else None
        )
        db.add(
            AiSignal(
                symbol=it["symbol"],
                side=it["side"],
                confidence=float(it["confidence"]),
                reason=it.get("reason"),
                source=source,
                expires_at=expires_at,
            )
        )
        n += 1
    db.commit()
    return n


def ingest_predictions(db: Session, *, items: list[dict]) -> int:
    n = 0
    for it in items:
        symbol = it["symbol"]
        asset = db.get(Asset, symbol)
        decimals = asset.decimals if asset else 18

        def maybe(v):
            if v is None:
                return None
            return str(to_base_units(v, decimals))

        db.add(
            AiPrediction(
                symbol=symbol,
                horizon=it["horizon"],
                predicted_price=maybe(it["predicted_price_human"]) or "0",
                lower_bound=maybe(it.get("lower_bound_human")),
                upper_bound=maybe(it.get("upper_bound_human")),
                confidence=float(it["confidence"]),
                model_tag=it.get("model_tag"),
            )
        )
        n += 1
    db.commit()
    return n


def ingest_sentiments(db: Session, *, items: list[dict]) -> int:
    n = 0
    for it in items:
        symbol = it["symbol"]
        asset = db.get(Asset, symbol)
        decimals = asset.decimals if asset else 18
        ma7 = (
            str(to_base_units(it["ma7_human"], decimals))
            if it.get("ma7_human") is not None
            else None
        )
        ma25 = (
            str(to_base_units(it["ma25_human"], decimals))
            if it.get("ma25_human") is not None
            else None
        )
        db.add(
            AiSentiment(
                symbol=symbol,
                sentiment_score=int(it["sentiment_score"]),
                rsi=it.get("rsi"),
                macd=it.get("macd"),
                ma7=ma7,
                ma25=ma25,
                extra_json=it.get("extra_json"),
            )
        )
        n += 1
    db.commit()
    return n


def list_signals(db: Session, *, symbol: str | None = None, limit: int = 50) -> list[dict]:
    q = select(AiSignal).order_by(AiSignal.created_at.desc()).limit(limit)
    if symbol:
        q = q.where(AiSignal.symbol == symbol)
    rows = list(db.execute(q).scalars())
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "side": r.side,
            "confidence": r.confidence,
            "reason": r.reason,
            "source": r.source,
            "created_at": r.created_at.isoformat(),
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        }
        for r in rows
    ]


def list_predictions(
    db: Session, *, symbol: str | None = None, horizon: str | None = None, limit: int = 50
) -> list[dict]:
    q = select(AiPrediction).order_by(AiPrediction.created_at.desc()).limit(limit)
    if symbol:
        q = q.where(AiPrediction.symbol == symbol)
    if horizon:
        q = q.where(AiPrediction.horizon == horizon)
    rows = list(db.execute(q).scalars())
    out = []
    for r in rows:
        asset = db.get(Asset, r.symbol)
        decimals = asset.decimals if asset else 18
        out.append(
            {
                "id": r.id,
                "symbol": r.symbol,
                "horizon": r.horizon,
                "predicted_price": to_human(int(r.predicted_price), decimals),
                "lower_bound": to_human(int(r.lower_bound), decimals) if r.lower_bound else None,
                "upper_bound": to_human(int(r.upper_bound), decimals) if r.upper_bound else None,
                "confidence": r.confidence,
                "model_tag": r.model_tag,
                "created_at": r.created_at.isoformat(),
            }
        )
    return out


def latest_sentiment(db: Session, *, symbol: str) -> dict | None:
    row = db.execute(
        select(AiSentiment)
        .where(AiSentiment.symbol == symbol)
        .order_by(AiSentiment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    asset = db.get(Asset, symbol)
    decimals = asset.decimals if asset else 18
    return {
        "id": row.id,
        "symbol": row.symbol,
        "sentiment_score": row.sentiment_score,
        "rsi": row.rsi,
        "macd": row.macd,
        "ma7": to_human(int(row.ma7), decimals) if row.ma7 else None,
        "ma25": to_human(int(row.ma25), decimals) if row.ma25 else None,
        "created_at": row.created_at.isoformat(),
    }
