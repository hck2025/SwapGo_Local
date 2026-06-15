from pydantic import BaseModel


class CreateBotReq(BaseModel):
    label: str
    scopes: list[str]


class CreateBotResp(BaseModel):
    user_id: int
    api_key_ONCE: str
    scopes: list[str]
    warning: str = "API 키는 이 응답에서만 표시되며 다시 확인할 수 없습니다."


class CreateAssetReq(BaseModel):
    symbol: str
    name: str
    decimals: int = 18
    logo_url: str | None = None
