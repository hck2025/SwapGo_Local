from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_current_user, get_db, wallet_actor
from app.schemas.wallet import DepositReq, WithdrawReq
from app.services import holdings_service, wallet_service

router = APIRouter()


@router.get("/me")
def my_wallet(
    wallet=Depends(wallet_actor()),
    db: Session = Depends(get_db),
):
    items = wallet_service.list_balances(db, wallet_id=wallet.id)
    return envelope_ok({"address": wallet.address, "balances": items})


@router.get("/holdings")
def my_holdings(
    wallet=Depends(wallet_actor()),
    db: Session = Depends(get_db),
):
    """보유 자산별 평균 매수단가·현재가·평가손익(수익률) + 포트폴리오 합계."""
    data = holdings_service.compute_holdings(db, wallet_id=wallet.id)
    return envelope_ok({"address": wallet.address, **data})


@router.post("/deposit/mock")
def deposit(
    req: DepositReq,
    wallet=Depends(wallet_actor()),
    db: Session = Depends(get_db),
):
    return envelope_ok(
        wallet_service.deposit_mock(
            db, wallet=wallet, symbol=req.symbol, amount_human=req.amount
        )
    )


@router.post("/withdraw/mock")
def withdraw(
    req: WithdrawReq,
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    return envelope_ok(
        wallet_service.withdraw_mock(
            db,
            wallet=wallet,
            symbol=req.symbol,
            amount_human=req.amount,
            to_address=req.to_address,
        )
    )


@router.get("/qr")
def qr(
    symbol: str,
    user_wallet=Depends(get_current_user),
):
    _, wallet = user_wallet
    return envelope_ok(
        {
            "address": wallet.address,
            "symbol": symbol,
            "deposit_uri": f"swapgo:{wallet.address}?symbol={symbol}",
            "note": "모의 입금 화면용 주소예요. 실제 송금은 받지 않아요.",
        }
    )
