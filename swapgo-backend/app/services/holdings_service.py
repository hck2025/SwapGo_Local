"""보유자산 + 평균 매수단가(cost basis) + 평가손익 계산.

지갑의 거래 원장을 시간순으로 재생(replay)해 자산별 **이동평균 매수단가**(USDT 기준)를
구한다. 사용자가 "내가 산 가격 대비 지금 얼마나 올랐/내렸는지"(수익률)를 볼 수 있게 한다.

- 매수 스왑(USDT→코인): 지불한 USDT 가 곧 취득원가. qty·cost 누적.
- 매도 스왑(코인→USDT): 평균단가로 원가를 차감(수량만큼). 평균단가는 유지.
- 입금(코인): 매수가 아니므로 입금 시점 시장가(가장 가까운 1m 캔들 close)로 평가.
  과거 캔들이 없으면 현재가로 폴백.
- 입금/출금 USDT: 기준통화라 손익 개념이 없어 제외.
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.balance import Balance
from app.db.models.candle import Candle
from app.db.models.pool import Pool
from app.db.models.transaction import Transaction

QUOTE = "USDT"


def _pow10(n: int) -> Decimal:
    return Decimal(10) ** n


def _current_price(pool: Pool, dec: dict[str, int]) -> Decimal:
    """풀 준비금으로 사람단위 현재가 산출 (chart_service 와 동일 규약)."""
    rb = Decimal(int(pool.reserve_base or 0))
    rq = Decimal(int(pool.reserve_quote or 0))
    if rb == 0:
        return Decimal(0)
    scale = _pow10(dec.get(pool.base_symbol, 18) - dec.get(pool.quote_symbol, 18))
    return (rq / rb) * scale


def _hist_price(db: Session, pool: Pool | None, ts, dec: dict[str, int]) -> Decimal:
    """입금 시점(ts) 직전의 1m 캔들 close(사람단위). 없으면 현재가로 폴백."""
    if pool is None:
        return Decimal(0)
    try:
        candle = db.execute(
            select(Candle)
            .where(
                Candle.pool_id == pool.id,
                Candle.interval == "1m",
                Candle.bucket_start <= ts,
            )
            .order_by(Candle.bucket_start.desc())
            .limit(1)
        ).scalar_one_or_none()
        if candle is not None:
            return Decimal(candle.close)
    except Exception:
        pass
    return _current_price(pool, dec)


def compute_holdings(db: Session, *, wallet_id: int) -> dict:
    assets = {a.symbol: a for a in db.execute(select(Asset)).scalars()}
    dec = {s: a.decimals for s, a in assets.items()}

    # base 심볼 → 풀 (quote=USDT 인 풀만)
    pool_by_base: dict[str, Pool] = {
        p.base_symbol: p
        for p in db.execute(select(Pool)).scalars()
        if p.quote_symbol == QUOTE
    }

    # 자산별 [보유수량, 누적원가(USDT)] 이동평균 상태
    state: dict[str, list[Decimal]] = {}

    def st(sym: str) -> list[Decimal]:
        return state.setdefault(sym, [Decimal(0), Decimal(0)])

    def buy(sym: str, qty: Decimal, cost: Decimal) -> None:
        x = st(sym)
        x[0] += qty
        x[1] += cost

    def reduce(sym: str, qty: Decimal) -> None:
        x = st(sym)
        if x[0] > 0:
            avg = x[1] / x[0]
            take = min(qty, x[0])
            x[1] -= avg * take
            x[0] -= take
        if x[0] < 0:
            x[0] = Decimal(0)

    txs = db.execute(
        select(Transaction)
        .where(Transaction.actor_wallet_id == wallet_id)
        .order_by(Transaction.id.asc())
    ).scalars()

    for tx in txs:
        try:
            p = json.loads(tx.payload_json)
        except Exception:
            continue
        t = tx.tx_type

        if t in ("swap", "bot_swap"):
            insym, outsym = p.get("in_symbol"), p.get("out_symbol")
            if not insym or not outsym:
                continue
            in_h = Decimal(str(p.get("amount_in", "0"))) / _pow10(dec.get(insym, 18))
            out_h = Decimal(str(p.get("amount_out", "0"))) / _pow10(dec.get(outsym, 18))
            if insym == QUOTE and outsym != QUOTE:        # 코인 매수
                buy(outsym, out_h, in_h)
            elif outsym == QUOTE and insym != QUOTE:      # 코인 매도
                reduce(insym, in_h)
            # 코인↔코인은 현재 풀 구성상 없음

        elif t == "deposit":
            sym = p.get("symbol")
            if not sym or sym == QUOTE:
                continue
            amt_h = Decimal(str(p.get("amount", "0"))) / _pow10(dec.get(sym, 18))
            price = _hist_price(db, pool_by_base.get(sym), tx.created_at, dec)
            buy(sym, amt_h, amt_h * price)

        elif t == "withdraw":
            sym = p.get("symbol")
            if not sym or sym == QUOTE:
                continue
            amt_h = Decimal(str(p.get("amount", "0"))) / _pow10(dec.get(sym, 18))
            reduce(sym, amt_h)

    # 현재 잔고 기준으로 항목 구성
    balances = db.execute(
        select(Balance).where(Balance.wallet_id == wallet_id)
    ).scalars()

    items: list[dict] = []
    total_value = Decimal(0)   # 전체 평가액(USDT 현금 포함)
    total_cost = Decimal(0)    # 원가 보유 자산의 투자원금 합
    total_pnl = Decimal(0)     # 원가 보유 자산의 평가손익 합
    for b in balances:
        sym = b.asset_symbol
        amt = Decimal(int(b.amount or 0)) / _pow10(dec.get(sym, 18))
        if amt <= 0:
            continue

        if sym == QUOTE:
            cur = Decimal(1)
        else:
            pool = pool_by_base.get(sym)
            cur = _current_price(pool, dec) if pool else Decimal(0)

        qty, cost = st(sym)
        avg = (cost / qty) if qty > 0 else None
        value = amt * cur
        total_value += value

        pnl_pct = None
        pnl_value = None
        invested = None
        if sym != QUOTE and avg is not None and avg > 0:
            invested = amt * avg
            pnl_value = (cur - avg) * amt
            pnl_pct = float((cur - avg) / avg * 100)
            total_cost += invested
            total_pnl += pnl_value

        items.append({
            "symbol": sym,
            "amount_human": _fmt(amt, dec.get(sym, 18)),
            "current_price_human": _fmt(cur, 2),
            "value_quote_human": _fmt(value, 2),
            "avg_cost_human": _fmt(avg, 2) if avg is not None else None,
            "invested_quote_human": _fmt(invested, 2) if invested is not None else None,
            "pnl_value_human": _fmt(pnl_value, 2) if pnl_value is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        })

    items.sort(key=lambda it: Decimal(it["value_quote_human"]), reverse=True)

    has_cost = total_cost > 0
    return {
        "total_value_quote_human": _fmt(total_value, 2),
        "total_invested_quote_human": _fmt(total_cost, 2) if has_cost else None,
        "total_pnl_value_human": _fmt(total_pnl, 2) if has_cost else None,
        "total_pnl_pct": (
            round(float(total_pnl / total_cost * 100), 2) if has_cost else None
        ),
        "items": items,
    }


def _fmt(d: Decimal | None, places: int) -> str:
    if d is None:
        return "0"
    q = Decimal(10) ** -places
    return str(d.quantize(q))
