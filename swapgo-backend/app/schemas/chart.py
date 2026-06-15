from pydantic import BaseModel


class CandleRow(BaseModel):
    bucket_start: str
    open: str
    high: str
    low: str
    close: str
    volume_base: str
    volume_quote: str
    trades_count: int


class CandlesResp(BaseModel):
    pool_id: int
    interval: str
    candles: list[CandleRow]


class TickerResp(BaseModel):
    pool_id: int
    last_price: str
    high_24h: str
    low_24h: str
    change_24h_pct: float
    volume_24h_base: str
    volume_24h_quote: str
