from pydantic import BaseModel, Field


class BalanceItem(BaseModel):
    symbol: str
    amount: str  # 정수 최소단위 직렬화
    amount_human: str
    decimals: int


class WalletMeResp(BaseModel):
    address: str
    balances: list[BalanceItem]


class DepositReq(BaseModel):
    symbol: str
    amount: str  # 사람이 읽는 단위 (예: "100" USDT)


class WithdrawReq(BaseModel):
    symbol: str
    amount: str
    to_address: str = Field(min_length=4)


class MockTxResp(BaseModel):
    tx_id: int
    tx_hash: str
    new_balance: str
    new_balance_human: str
