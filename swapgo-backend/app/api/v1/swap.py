from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db, wallet_actor
from app.schemas.swap import ExecuteReq, QuoteReq
from app.services import swap_service

router = APIRouter()


@router.post("/quote")
def quote(req: QuoteReq, db: Session = Depends(get_db)):
    return envelope_ok(
        swap_service.build_quote(
            db,
            pool_id=req.pool_id,
            side=req.side,
            amount_in_human=req.amount_in_human,
            slippage_tolerance_bps=req.slippage_tolerance_bps,
        )
    )


@router.post("/execute")
def execute(
    req: ExecuteReq,
    wallet=Depends(wallet_actor(required_bot_scope="bot:trade")),
    db: Session = Depends(get_db),
):
    try:
        return envelope_ok(
            swap_service.execute_swap(
                db,
                wallet=wallet,
                pool_id=req.pool_id,
                side=req.side,
                amount_in_human=req.amount_in_human,
                min_amount_out=req.min_amount_out,
                slippage_tolerance_bps=req.slippage_tolerance_bps,
                expected_revision=req.expected_revision,
            )
        )
    except Exception as e:
        # 이 부분이 범인을 밝혀줄 핵심 로그입니다.
        print(f"DEBUG: execute 실패 상세 이유 -> {str(e)}")
        # 에러를 다시 던져서 봇이 인지하게 함
        raise e