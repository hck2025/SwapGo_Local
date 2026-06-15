"""사람이 읽는 단위 ↔ 정수 최소단위 변환. 부동소수 절대 사용 안 함."""

from __future__ import annotations

from decimal import Decimal, getcontext

getcontext().prec = 80


def to_base_units(amount_human: str, decimals: int) -> int:
    d = Decimal(amount_human)
    if d < 0:
        raise ValueError("음수 수량은 허용되지 않아요.")
    scaled = d * (Decimal(10) ** decimals)
    # 절단(소수점 아래 잘라냄)
    return int(scaled.to_integral_value(rounding="ROUND_DOWN"))


def to_human(amount_base: int | str, decimals: int) -> str:
    n = int(amount_base)
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    s = str(n).rjust(decimals + 1, "0")
    int_part = s[:-decimals] if decimals > 0 else s
    frac_part = s[-decimals:] if decimals > 0 else ""
    frac_part = frac_part.rstrip("0")
    if frac_part:
        return f"{sign}{int_part}.{frac_part}"
    return f"{sign}{int_part}"
