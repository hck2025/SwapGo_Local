from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.db.models.asset import Asset
from app.deps import get_db
from app.services import market_service, pool_service
from app.services.orderbook_synth import synth_orderbook

router = APIRouter()


@router.get("/coins")
def coins(db: Session = Depends(get_db)):
    return envelope_ok({"coins": market_service.list_coins(db)})


@router.get("/global")
def global_(db: Session = Depends(get_db)):
    return envelope_ok(market_service.global_market(db))


def _fmt(x: float) -> str:
    # 주의: 이 문자열은 프론트엔드가 parseFloat() 로 파싱한다. 천 단위 콤마(,)를
    # 넣으면 parseFloat("2,840")==2 로 끊겨 호가창 가격/중간가가 깨지므로 콤마 금지.
    if x == 0:
        return "0"
    if x >= 1:
        s = f"{x:.4f}"
    else:
        s = f"{x:.10f}"
    return s.rstrip("0").rstrip(".") or "0"


@router.get("/orderbook")
def orderbook(
    pool_id: int,
    levels: int = Query(default=12, ge=1, le=50),
    step_pct: float = Query(default=0.001, gt=0, le=0.1),
    db: Session = Depends(get_db),
):
    pool = pool_service.get_pool(db, pool_id)
    base = db.get(Asset, pool.base_symbol)
    quote = db.get(Asset, pool.quote_symbol)
    base_dec = base.decimals if base else 18
    quote_dec = quote.decimals if quote else 18

    book = synth_orderbook(
        int(pool.reserve_base or 0),
        int(pool.reserve_quote or 0),
        fee_bps=pool.fee_bps,
        levels=levels,
        step_pct=step_pct,
    )

    # decimals 보정: raw price * 10^(base_dec - quote_dec) = human price
    price_scale = 10 ** (base_dec - quote_dec)
    base_unit = 10 ** base_dec

    def conv(level: dict) -> dict:
        return {
            "price": _fmt(level["price_raw"] * price_scale),
            "size": _fmt(level["size_base_raw"] / base_unit),
            "cum_size": _fmt(level["cum_base_raw"] / base_unit),
        }

    out = {
        "pool_id": pool.id,
        "revision": pool.revision,
        "mid": _fmt(book["mid_raw"] * price_scale),
        "bids": [conv(b) for b in book["bids"]],
        "asks": [conv(a) for a in book["asks"]],
        "base_symbol": pool.base_symbol,
        "quote_symbol": pool.quote_symbol,
        "glossary_keys": ["amm", "liquidity_pool", "price_impact"],
        "friendly_message": (
            "AMM에는 실제 호가창이 없어요. 풀의 가격을 단계별로 옮기는 데 필요한 "
            f"{pool.base_symbol} 수량을 시각화해 보여드려요."
        ),
    }
    return envelope_ok(out)


@router.get("/trades")
def trades(
    pool_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return envelope_ok(market_service.recent_trades(db, pool_id=pool_id, limit=limit))
