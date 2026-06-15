"""순수 CPMM(x*y=k) 계산. DB 의존성 없음 — 단위테스트 용이.

수량은 모두 정수 최소단위. 부동소수는 표시/슬리피지 비교용 보조 계산에만.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.errors import InsufficientLiquidity, InvalidAmount


@dataclass(frozen=True)
class QuoteResult:
    amount_in: int
    amount_out: int
    fee_amount: int
    fee_bps: int
    new_reserve_in: int
    new_reserve_out: int
    mid_price_before: float  # quote_per_in_unit
    mid_price_after: float
    execution_price: float
    price_impact_bps: int
    slippage_bps: int


def quote_swap(
    reserve_in: int,
    reserve_out: int,
    amount_in: int,
    fee_bps: int = 30,
) -> QuoteResult:
    """`reserve_in` 자산을 amount_in 만큼 넣고 `reserve_out` 자산을 받는다.

    Uniswap V2 동치: amount_out = (amount_in * (10000-fee_bps) * reserve_out)
                                / (reserve_in*10000 + amount_in*(10000-fee_bps))
    """
    if amount_in <= 0:
        raise InvalidAmount()
    if reserve_in <= 0 or reserve_out <= 0:
        raise InsufficientLiquidity()

    fee_amount = amount_in * fee_bps // 10000
    in_after_fee = amount_in - fee_amount

    numerator = reserve_out * in_after_fee
    denominator = reserve_in + in_after_fee
    amount_out = numerator // denominator

    if amount_out <= 0 or amount_out >= reserve_out:
        raise InsufficientLiquidity()

    new_reserve_in = reserve_in + amount_in
    new_reserve_out = reserve_out - amount_out

    mid_before = reserve_out / reserve_in
    mid_after = new_reserve_out / new_reserve_in
    execution_price = amount_out / amount_in

    price_impact_bps = round((mid_before - mid_after) / mid_before * 10000)
    slippage_bps = round((mid_before - execution_price) / mid_before * 10000)

    return QuoteResult(
        amount_in=amount_in,
        amount_out=amount_out,
        fee_amount=fee_amount,
        fee_bps=fee_bps,
        new_reserve_in=new_reserve_in,
        new_reserve_out=new_reserve_out,
        mid_price_before=mid_before,
        mid_price_after=mid_after,
        execution_price=execution_price,
        price_impact_bps=max(0, price_impact_bps),
        slippage_bps=max(0, slippage_bps),
    )


def classify_slippage(
    slippage_bps: int, *, warn_bps: int = 50, danger_bps: int = 300
) -> str:
    if slippage_bps < warn_bps:
        return "safe"
    if slippage_bps < danger_bps:
        return "warning"
    return "danger"


def auto_slippage_tolerance_bps(price_impact_bps: int, *, floor_bps: int = 50) -> int:
    """슬리피지 미입력 시 자동값. price_impact 의 1.5배에 안전 floor 적용."""
    return max(floor_bps, math.ceil(price_impact_bps * 1.5))


def quote_add_liquidity_proportional(
    reserve_base: int,
    reserve_quote: int,
    base_amount: int,
    *,
    total_lp_shares: int,
) -> tuple[int, int]:
    """현재 풀 비율에 맞춘 quote 수량과 발행 LP 지분을 계산.

    초기 유동성: shares = sqrt(base*quote)
    추가 공급:   shares = total_lp * base_amount / reserve_base
    """
    if base_amount <= 0:
        raise InvalidAmount()
    if reserve_base == 0 and reserve_quote == 0:
        # 초기 유동성: quote_amount는 호출자가 자유롭게 지정해야 함 → 여기선 base_amount만 강제
        raise InvalidAmount("초기 풀은 base와 quote를 명시적으로 지정해야 해요.")

    quote_amount = (base_amount * reserve_quote + reserve_base - 1) // reserve_base  # 올림
    shares = (base_amount * total_lp_shares) // reserve_base if total_lp_shares > 0 else 0
    return quote_amount, shares


def initial_lp_shares(base_amount: int, quote_amount: int) -> int:
    if base_amount <= 0 or quote_amount <= 0:
        raise InvalidAmount()
    return int(math.isqrt(base_amount * quote_amount))


def quote_remove_liquidity(
    reserve_base: int,
    reserve_quote: int,
    total_lp_shares: int,
    shares: int,
) -> tuple[int, int]:
    if shares <= 0 or shares > total_lp_shares:
        raise InvalidAmount("회수할 지분이 올바르지 않아요.")
    base_out = reserve_base * shares // total_lp_shares
    quote_out = reserve_quote * shares // total_lp_shares
    return base_out, quote_out


def pool_price(reserve_base: int, reserve_quote: int) -> float:
    if reserve_base == 0:
        return 0.0
    return reserve_quote / reserve_base
