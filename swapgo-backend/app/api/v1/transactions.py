"""사용자 본인의 거래내역 + 통계 + CSV."""

from __future__ import annotations

import csv
import io
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_current_user, get_db
from app.db.models.transaction import Transaction
from app.db.models.wallet import Wallet

router = APIRouter()


def _row_to_dict(r: Transaction, address: str | None) -> dict:
    return {
        "id": r.id,
        "tx_type": r.tx_type,
        "pool_id": r.pool_id,
        "actor_wallet_id": r.actor_wallet_id,
        "actor_address": address,
        "amount_in": str(int(r.amount_in)) if r.amount_in is not None else None,
        "amount_out": str(int(r.amount_out)) if r.amount_out is not None else None,
        "fee_amount": str(int(r.fee_amount)) if r.fee_amount is not None else None,
        "slippage_bps": r.slippage_bps,
        "price_after": r.price_after,
        "prev_hash": r.prev_hash,
        "tx_hash": r.tx_hash,
        "payload": json.loads(r.payload_json),
        "created_at": r.created_at.isoformat(),
    }


@router.get("/transactions")
def my_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    type: str | None = Query(default=None),
    pool: int | None = Query(default=None),
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    q = select(Transaction).where(Transaction.actor_wallet_id == wallet.id)
    if type:
        q = q.where(Transaction.tx_type == type)
    if pool is not None:
        q = q.where(Transaction.pool_id == pool)
    total = db.execute(
        select(func.count()).select_from(q.subquery())
    ).scalar_one()
    rows = list(
        db.execute(
            q.order_by(Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars()
    )
    return envelope_ok(
        {
            "items": [_row_to_dict(r, wallet.address) for r in rows],
            "page": page,
            "page_size": page_size,
            "total": int(total),
        }
    )


@router.get("/transactions.csv")
def my_transactions_csv(
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet

    def _stream():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "id",
                "tx_type",
                "pool_id",
                "amount_in",
                "amount_out",
                "fee_amount",
                "slippage_bps",
                "price_after",
                "tx_hash",
                "created_at",
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        rows = db.execute(
            select(Transaction)
            .where(Transaction.actor_wallet_id == wallet.id)
            .order_by(Transaction.id.asc())
        ).scalars()
        for r in rows:
            writer.writerow(
                [
                    r.id,
                    r.tx_type,
                    r.pool_id or "",
                    int(r.amount_in or 0),
                    int(r.amount_out or 0),
                    int(r.fee_amount or 0),
                    r.slippage_bps or "",
                    r.price_after or "",
                    r.tx_hash,
                    r.created_at.isoformat(),
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        _stream(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="my-transactions.csv"'},
    )


@router.get("/stats")
def my_stats(
    user_wallet=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, wallet = user_wallet
    rows = list(
        db.execute(
            select(Transaction).where(
                Transaction.actor_wallet_id == wallet.id,
                Transaction.tx_type.in_(("swap", "bot_swap")),
            )
        ).scalars()
    )
    trade_count = len(rows)
    total_fees = sum(Decimal(int(r.fee_amount or 0)) for r in rows)
    total_volume = sum(Decimal(int(r.amount_in or 0)) for r in rows)
    return envelope_ok(
        {
            "trade_count": trade_count,
            "total_fees_paid_quote_human": str(total_fees),
            "total_volume_quote_human": str(total_volume),
            "win_rate_pct": None,
            "note": "현재 모의 거래는 단일 풀 가격에 의존해 손익 계산이 단순합니다.",
        }
    )
