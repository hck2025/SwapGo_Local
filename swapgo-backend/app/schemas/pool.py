from pydantic import BaseModel


class PoolResp(BaseModel):
    id: int
    base_symbol: str
    quote_symbol: str
    reserve_base: str
    reserve_quote: str
    reserve_base_human: str
    reserve_quote_human: str
    price: str
    fee_bps: int
    is_active: bool
    revision: int
    tvl_quote_human: str | None = None


class CreatePoolReq(BaseModel):
    base_symbol: str
    quote_symbol: str
    init_base_human: str
    init_quote_human: str
    fee_bps: int = 30
