from pydantic import BaseModel, Field


class SignupReq(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)


class SignupResp(BaseModel):
    address: str
    public_key_hex: str
    private_key_ONCE: str
    mnemonic_ONCE: str
    warning: str = (
        "이 화면을 벗어나면 개인키와 니모닉은 다시 표시되지 않아요. "
        "안전한 곳에 보관하지 않으면 계정 복구가 불가능합니다."
    )


class ChallengeReq(BaseModel):
    address: str


class ChallengeResp(BaseModel):
    nonce: str
    message: str
    expires_at: str


class LoginReq(BaseModel):
    address: str
    signature: str
    nonce: str


class LoginResp(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    address: str
