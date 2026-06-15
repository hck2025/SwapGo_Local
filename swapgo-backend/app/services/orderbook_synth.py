"""AMM 풀로부터 가상 호가창(orderbook)을 합성한다.

- size 는 모두 **base 자산 raw 단위**로 통일 (시안의 "수량(BTC)" 컬럼과 매칭).
- 라우터가 decimals 를 적용해 사람 단위로 변환해 응답한다.
"""

from __future__ import annotations

import math


def synth_orderbook(
    reserve_base: int,
    reserve_quote: int,
    *,
    fee_bps: int = 30,
    levels: int = 12,
    step_pct: float = 0.001,
) -> dict:
    if reserve_base <= 0 or reserve_quote <= 0:
        return {"mid": 0.0, "bids": [], "asks": []}

    rb = float(reserve_base)
    rq = float(reserve_quote)
    k = rb * rq
    mid = rq / rb
    fee_factor = 10000 / max(1, 10000 - fee_bps)

    asks: list[dict] = []  # 가격 상승 — 유저가 quote 넣고 base 받음
    cum = 0.0
    for i in range(1, levels + 1):
        target = mid * (1 + i * step_pct)
        new_rb = math.sqrt(k / target)
        if new_rb >= rb or new_rb <= 0:
            break
        base_out = rb - new_rb  # 누적 base 받을 양
        size_in_base = base_out - cum
        cum = base_out
        if size_in_base <= 0:
            break
        asks.append(
            {
                "price_raw": target,
                "size_base_raw": size_in_base,
                "cum_base_raw": cum,
            }
        )

    bids: list[dict] = []  # 가격 하락 — 유저가 base 넣고 quote 받음
    cum = 0.0
    for i in range(1, levels + 1):
        target = mid * (1 - i * step_pct)
        if target <= 0:
            break
        new_rb = math.sqrt(k / target)
        if new_rb <= rb:
            break
        base_in_net = new_rb - rb
        base_in_gross = base_in_net * fee_factor
        size_in_base = base_in_gross - cum
        cum = base_in_gross
        if size_in_base <= 0:
            break
        bids.append(
            {
                "price_raw": target,
                "size_base_raw": size_in_base,
                "cum_base_raw": cum,
            }
        )

    return {"mid_raw": mid, "bids": bids, "asks": asks}
