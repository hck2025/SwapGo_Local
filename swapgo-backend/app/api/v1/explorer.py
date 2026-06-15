"""인증 불필요한 공개 익스플로러 — DEX 무결성 가치를 시각화."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db
from app.db.models.merkle_snapshot import MerkleSnapshot
from app.db.models.transaction import Transaction
from app.db.models.wallet import Wallet
from app.services import ledger_service

router = APIRouter()


def _to_dict(r: Transaction, address: str | None) -> dict:
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


@router.get("/tx/{tx_id}")
def get_tx(tx_id: int, db: Session = Depends(get_db)):
    r = db.get(Transaction, tx_id)
    if r is None:
        return envelope_ok(None)
    addr = None
    if r.actor_wallet_id:
        w = db.get(Wallet, r.actor_wallet_id)
        addr = w.address if w else None
    payload = _to_dict(r, addr)
    payload["friendly_message"] = (
        "이 거래는 직전 거래 해시(prev_hash)와 본인 페이로드를 이어붙여 sha256으로 해시한 결과예요. "
        "다른 사용자도 동일한 알고리즘으로 검증할 수 있어요."
    )
    payload["glossary_keys"] = ["amm", "liquidity_pool"]
    return envelope_ok(payload)


@router.get("/blocks")
def list_blocks(
    from_id: int = Query(default=1, ge=1, alias="from"),
    to: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = select(Transaction).where(Transaction.id >= from_id)
    if to is not None:
        q = q.where(Transaction.id <= to)
    q = q.order_by(Transaction.id.asc()).limit(limit)
    rows = list(db.execute(q).scalars())
    out = []
    for r in rows:
        addr = None
        if r.actor_wallet_id:
            w = db.get(Wallet, r.actor_wallet_id)
            addr = w.address if w else None
        out.append(_to_dict(r, addr))
    return envelope_ok(out)


@router.get("/wallet/{address}")
def by_wallet(address: str, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    w = db.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
    if w is None:
        return envelope_ok({"address": address, "items": []})
    rows = list(
        db.execute(
            select(Transaction)
            .where(Transaction.actor_wallet_id == w.id)
            .order_by(Transaction.id.desc())
            .limit(limit)
        ).scalars()
    )
    return envelope_ok(
        {"address": address, "items": [_to_dict(r, address) for r in rows]}
    )


@router.get("/pools/{pool_id}/history")
def pool_history(pool_id: int, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = list(
        db.execute(
            select(Transaction)
            .where(Transaction.pool_id == pool_id)
            .order_by(Transaction.id.desc())
            .limit(limit)
        ).scalars()
    )
    return envelope_ok([_to_dict(r, None) for r in rows])


@router.get("/merkle/latest")
def latest_merkle(db: Session = Depends(get_db)):
    r = db.execute(
        select(MerkleSnapshot).order_by(MerkleSnapshot.id.desc()).limit(1)
    ).scalar_one_or_none()
    if r is None:
        return envelope_ok(None)
    return envelope_ok(
        {
            "id": r.id,
            "from_tx_id": r.from_tx_id,
            "to_tx_id": r.to_tx_id,
            "merkle_root": r.merkle_root,
            "tx_count": r.tx_count,
            "created_at": r.created_at.isoformat(),
        }
    )


@router.get("/verify")
def verify(
    from_id: int = Query(default=1, ge=1, alias="from"),
    to: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    result = ledger_service.verify_chain(db, from_id=from_id, to_id=to)
    result["friendly_message"] = (
        "이 구간 거래들의 prev_hash → tx_hash 체인을 다시 계산해 위변조 여부를 확인했어요. "
        "결과 머클루트는 직접 sha256으로 재계산해 비교할 수 있어요."
    )
    result["glossary_keys"] = ["amm", "liquidity_pool"]
    return envelope_ok(result)
