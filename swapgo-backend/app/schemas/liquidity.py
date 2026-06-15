from pydantic import BaseModel


class AddLiquidityQuoteReq(BaseModel):
    pool_id: int
    base_amount_human: str


class AddLiquidityQuoteResp(BaseModel):
    pool_id: int
    base_amount: str
    quote_amount: str
    base_amount_human: str
    quote_amount_human: str
    estimated_shares: str
    is_initial: bool


class AddLiquidityReq(BaseModel):
    pool_id: int
    base_amount_human: str
    quote_amount_human: str
    min_shares: str = "0"


class RemoveLiquidityReq(BaseModel):
    pool_id: int
    shares: str
    min_base: str = "0"
    min_quote: str = "0"


class LiquidityResultResp(BaseModel):
    tx_id: int
    tx_hash: str
    shares_delta: str
    base_delta: str
    quote_delta: str
    pool_after_reserve_base: str
    pool_after_reserve_quote: str


class LiquidityPositionResp(BaseModel):
    pool_id: int
    base_symbol: str
    quote_symbol: str
    shares: str
    pool_share_pct: float
