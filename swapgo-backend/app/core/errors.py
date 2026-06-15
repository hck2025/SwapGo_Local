"""초보자 친화 한국어 에러 메시지.

각 에러는 code(영문 식별자) + message(현상) + suggestion(대처) + glossary_keys(관련 용어)
를 함께 노출해 프론트가 에러 토스트와 용어 학습을 동시에 제공할 수 있게 한다.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """API 응답 봉투의 error 필드로 변환되는 도메인 예외."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "요청을 처리할 수 없어요."
    suggestion: str = ""
    glossary_keys: list[str] = []

    def __init__(
        self,
        message: str | None = None,
        *,
        suggestion: str | None = None,
        glossary_keys: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message or self.message
        self.suggestion = suggestion if suggestion is not None else self.suggestion
        self.glossary_keys = glossary_keys if glossary_keys is not None else self.glossary_keys
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "glossary_keys": list(self.glossary_keys),
            "details": self.details,
        }


# ----- 인증 -----
class WalletNotFound(AppError):
    status_code = 404
    code = "WALLET_NOT_FOUND"
    message = "등록되지 않은 지갑 주소예요."
    suggestion = "회원가입을 먼저 진행해주세요."


class InvalidSignature(AppError):
    status_code = 401
    code = "INVALID_SIGNATURE"
    message = "서명 검증에 실패했어요."
    suggestion = "올바른 개인키로 챌린지 메시지를 다시 서명해주세요."


class NonceExpired(AppError):
    status_code = 401
    code = "NONCE_EXPIRED"
    message = "로그인 챌린지가 만료되었어요."
    suggestion = "다시 챌린지 발급을 요청해주세요."


class NonceAlreadyUsed(AppError):
    status_code = 401
    code = "NONCE_ALREADY_USED"
    message = "이미 사용된 챌린지예요."
    suggestion = "새 챌린지를 발급받아 로그인해주세요."


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "로그인이 필요해요."


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "이 작업을 수행할 권한이 없어요."


# ----- 잔고/지갑 -----
class InsufficientBalance(AppError):
    status_code = 400
    code = "INSUFFICIENT_BALANCE"
    message = "잔고가 부족해요."
    suggestion = "보유 자산을 확인하거나 입금을 먼저 진행해주세요."


# ----- 풀/스왑 -----
class PoolNotFound(AppError):
    status_code = 404
    code = "POOL_NOT_FOUND"
    message = "해당 풀을 찾을 수 없어요."


class PoolInactive(AppError):
    status_code = 400
    code = "POOL_INACTIVE"
    message = "비활성화된 풀이에요."
    suggestion = "다른 거래쌍을 선택해주세요."
    glossary_keys = ["liquidity_pool"]


class InsufficientLiquidity(AppError):
    status_code = 400
    code = "INSUFFICIENT_LIQUIDITY"
    message = "풀의 유동성이 부족해서 이 거래를 처리할 수 없어요."
    suggestion = "거래 수량을 줄이거나, 유동성이 더 풍부한 시간대에 다시 시도해주세요."
    glossary_keys = ["liquidity_pool", "amm"]


class SlippageExceeded(AppError):
    status_code = 400
    code = "SLIPPAGE_EXCEEDED"
    message = "슬리피지 허용치를 초과했어요."
    suggestion = "수량을 줄이거나 슬리피지 허용치를 0.5%→1%로 높여보세요."
    glossary_keys = ["slippage", "price_impact"]


class StaleQuote(AppError):
    status_code = 409
    code = "STALE_QUOTE"
    message = "견적이 만료되었거나 풀 상태가 변경되었어요."
    suggestion = "견적을 다시 받아 거래를 진행해주세요."
    glossary_keys = ["slippage"]


class InvalidAmount(AppError):
    status_code = 400
    code = "INVALID_AMOUNT"
    message = "수량이 올바르지 않아요."
    suggestion = "0보다 큰 수량을 입력해주세요."


class DuplicatePool(AppError):
    status_code = 409
    code = "DUPLICATE_POOL"
    message = "이미 존재하는 풀이에요."
