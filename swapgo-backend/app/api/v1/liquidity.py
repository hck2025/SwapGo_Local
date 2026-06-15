from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_current_user, get_db
from app.schemas.liquidity import (
    AddLiquidityQuoteReq,
    AddLiquidityReq,
    RemoveLiquidityReq,
)
from app.services import liquidity_service

router = APIRouter()


@router.post("/quote-add")
def quote_add(req: AddLiquidityQuoteReq, db: Session = Depends(get_db)):
    return envelope_ok(
        liquidity_service.quote_add(
            db, pool_id=req.pool_id, base_amount_human=req.base_amount_human
        )
    )


@router.post("/add")
def add(
    req: AddLiquidityReq,
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    return envelope_ok(
        liquidity_service.add_liquidity(
            db,
            wallet=wallet,
            pool_id=req.pool_id,
            base_amount_human=req.base_amount_human,
            quote_amount_human=req.quote_amount_human,
            min_shares=req.min_shares,
        )
    )


@router.post("/remove")
def remove(
    req: RemoveLiquidityReq,
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    return envelope_ok(
        liquidity_service.remove_liquidity(
            db,
            wallet=wallet,
            pool_id=req.pool_id,
            shares=req.shares,
            min_base=req.min_base,
            min_quote=req.min_quote,
        )
    )


@router.get("/positions")
def positions(
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    return envelope_ok(liquidity_service.list_positions(db, wallet_id=wallet.id))
