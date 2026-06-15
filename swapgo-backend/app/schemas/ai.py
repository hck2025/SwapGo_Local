from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["buy", "sell", "hold"]
Horizon = Literal["1h", "24h", "7d"]


class SignalIn(BaseModel):
    symbol: str
    side: Side
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str | None = None
    expires_in_sec: int | None = None


class SignalsIngestReq(BaseModel):
    items: list[SignalIn]


class SignalOut(BaseModel):
    id: int
    symbol: str
    side: Side
    confidence: float
    reason: str | None
    source: str | None
    created_at: str
    expires_at: str | None


class PredictionIn(BaseModel):
    symbol: str
    horizon: Horizon
    predicted_price_human: str
    lower_bound_human: str | None = None
    upper_bound_human: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    model_tag: str | None = None


class PredictionsIngestReq(BaseModel):
    items: list[PredictionIn]


class PredictionOut(BaseModel):
    id: int
    symbol: str
    horizon: Horizon
    predicted_price: str
    lower_bound: str | None
    upper_bound: str | None
    confidence: float
    model_tag: str | None
    created_at: str


class SentimentIn(BaseModel):
    symbol: str
    sentiment_score: int = Field(ge=-100, le=100)
    rsi: float | None = None
    macd: float | None = None
    ma7_human: str | None = None
    ma25_human: str | None = None
    extra_json: str | None = None


class SentimentIngestReq(BaseModel):
    items: list[SentimentIn]


class SentimentOut(BaseModel):
    id: int
    symbol: str
    sentiment_score: int
    rsi: float | None
    macd: float | None
    ma7: str | None
    ma25: str | None
    created_at: str
