from pydantic import BaseModel


class CoinRow(BaseModel):
    symbol: str
    name: str
    price_human: str
    change_24h_pct: float
    volume_24h_human: str
    sparkline: list[float]
    pool_id: int | None = None


class MarketCoinsResp(BaseModel):
    coins: list[CoinRow]


class GlobalMarketResp(BaseModel):
    total_market_cap_usdt_human: str
    total_volume_24h_usdt_human: str
    btc_dominance_pct: float
    eth_dominance_pct: float
    note: str = "시장 통계는 거래소 내부 풀 가격을 기반으로 추정된 학습용 수치입니다."


class OrderbookLevel(BaseModel):
    price: str
    size: str
    cum_size: str


class OrderbookResp(BaseModel):
    pool_id: int
    mid_price: str
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    revision: int
    glossary_keys: list[str] = ["amm", "liquidity_pool"]
    friendly_message: str = (
        "AMM에는 실제 호가창이 없어요. 풀 가격을 단계별로 움직이는 데 필요한 수량을 표시해드려요."
    )


class TradeRow(BaseModel):
    tx_id: int
    side: str
    amount_in: str
    amount_out: str
    price: str
    slippage_level: str | None
    created_at: str
