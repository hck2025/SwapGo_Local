from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["base_to_quote", "quote_to_base"]
SlippageLevel = Literal["safe", "warning", "danger"]


class QuoteReq(BaseModel):
    pool_id: int
    side: Side
    amount_in_human: str
    slippage_tolerance_bps: int | None = Field(default=None, ge=0, le=10000)


class PoolAfter(BaseModel):
    reserve_base: str
    reserve_quote: str
    price: str
    revision: int


class QuoteResp(BaseModel):
    pool_id: int
    side: Side
    amount_in: str
    amount_in_human: str
    amount_out: str
    amount_out_human: str
    amount_out_min: str
    fee_amount: str
    fee_bps: int
    execution_price: str
    mid_price_before: str
    mid_price_after: str
    price_impact_bps: int
    slippage_bps: int
    slippage_level: SlippageLevel
    slippage_threshold_used_bps: int
    pool_after: PoolAfter
    friendly_message: str
    glossary_keys: list[str]
    quote_id: str
    expires_at: str


class ExecuteReq(BaseModel):
    pool_id: int
    side: Side
    amount_in_human: str
    min_amount_out: str  # 정수 최소단위 또는 human? — 일관성 위해 정수 최소단위 문자열
    slippage_tolerance_bps: int = Field(ge=0, le=10000)
    quote_id: str | None = None
    expected_revision: int | None = None


class ExecuteResp(BaseModel):
    tx_id: int
    tx_hash: str
    quote: QuoteResp
    explorer_url: str
