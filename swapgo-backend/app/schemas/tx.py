from typing import Any

from pydantic import BaseModel


class TxRow(BaseModel):
    id: int
    tx_type: str
    pool_id: int | None
    actor_wallet_id: int | None
    actor_address: str | None
    amount_in: str | None
    amount_out: str | None
    fee_amount: str | None
    slippage_bps: int | None
    price_after: str | None
    prev_hash: str
    tx_hash: str
    payload: dict[str, Any]
    created_at: str


class TxListResp(BaseModel):
    items: list[TxRow]
    page: int
    page_size: int
    total: int


class StatsResp(BaseModel):
    trade_count: int
    total_fees_paid_quote_human: str
    total_volume_quote_human: str
    win_rate_pct: float | None
    note: str = "승률/손익은 단순 가격 변동 기반 학습용 추정치입니다."


class ExplorerVerifyResp(BaseModel):
    ok: bool
    count: int
    start_id: int
    end_id: int | None
    first_invalid_id: int | None
    recomputed_root: str | None
    glossary_keys: list[str] = ["amm", "liquidity_pool"]
    friendly_message: str = (
        "이 구간의 거래들을 다시 해시 계산해 위변조가 없는지 확인했어요. "
        "직접 검증하고 싶다면 sha256(prev_hash + meta + payload) 공식을 사용하세요."
    )


class MerkleSnapshotResp(BaseModel):
    id: int
    from_tx_id: int
    to_tx_id: int
    merkle_root: str
    tx_count: int
    created_at: str
