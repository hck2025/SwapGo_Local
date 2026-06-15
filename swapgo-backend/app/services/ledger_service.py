"""체인형 해시 원장: prev_hash → tx_hash 로 연결되는 append-only 트랜잭션 로그.

모든 잔고/풀/유동성 변경은 이 모듈의 append_tx() 단일 진입점을 통해 기록되어야 한다.
검증은 verify_chain() 으로 누구나 재계산 가능 (/explorer/verify 에서 노출).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashing import GENESIS_PREV_HASH, canonical_json, compute_tx_hash, merkle_root
from app.core.time import kst_now
from app.db.models.transaction import Transaction


_TS_FIELD = "_ledger_ts"


def _meta_for(row: Transaction) -> dict:
    """tx_hash 재계산에 사용하는 메타. payload에 _ledger_ts 키가 들어있으므로
    여기서는 tx_type만 메타로 사용한다."""
    return {"tx_type": row.tx_type}


@dataclass
class AppendedTx:
    tx_id: int
    tx_hash: str
    prev_hash: str
    created_at_iso: str


def _last_tx_hash(db: Session) -> str:
    row = db.execute(
        select(Transaction.tx_hash).order_by(Transaction.id.desc()).limit(1)
    ).scalar_one_or_none()
    return row or GENESIS_PREV_HASH


def append_tx(
    db: Session,
    *,
    tx_type: str,
    payload: dict,
    actor_wallet_id: int | None = None,
    pool_id: int | None = None,
    amount_in: int | None = None,
    amount_out: int | None = None,
    fee_amount: int | None = None,
    slippage_bps: int | None = None,
    price_after: str | None = None,
) -> AppendedTx:
    """append-only. 호출자는 같은 SQLAlchemy 세션의 동일 트랜잭션 안에서
    잔고/풀/유동성 갱신과 함께 호출해 원자성을 보장해야 한다."""
    prev_hash = _last_tx_hash(db)
    now = kst_now()
    ts = now.isoformat()
    payload = dict(payload)
    payload[_TS_FIELD] = ts
    meta = {"tx_type": tx_type}
    leaf = compute_tx_hash(prev_hash, meta, payload)

    row = Transaction(
        tx_type=tx_type,
        actor_wallet_id=actor_wallet_id,
        pool_id=pool_id,
        payload_json=canonical_json(payload).decode("utf-8"),
        amount_in=amount_in,
        amount_out=amount_out,
        fee_amount=fee_amount,
        slippage_bps=slippage_bps,
        price_after=price_after,
        prev_hash=prev_hash,
        tx_hash=leaf,
        created_at=now,  # meta에 사용한 시각과 일치시켜 검증 가능
    )
    db.add(row)
    db.flush()  # id 확보
    return AppendedTx(tx_id=row.id, tx_hash=leaf, prev_hash=prev_hash, created_at_iso=ts)


def verify_chain(
    db: Session,
    *,
    from_id: int = 1,
    to_id: int | None = None,
) -> dict:
    """[from_id, to_id] 구간의 체인 무결성을 재계산하여 검증한다.

    반환: {ok, count, start_id, end_id, first_invalid_id, recomputed_root}
    """
    q = select(Transaction).where(Transaction.id >= from_id).order_by(Transaction.id.asc())
    if to_id is not None:
        q = q.where(Transaction.id <= to_id)
    rows: list[Transaction] = list(db.execute(q).scalars())
    if not rows:
        return {
            "ok": True,
            "count": 0,
            "start_id": from_id,
            "end_id": to_id,
            "first_invalid_id": None,
            "recomputed_root": GENESIS_PREV_HASH,
        }

    if from_id == 1:
        expected_prev = GENESIS_PREV_HASH
    else:
        prev_row = db.execute(
            select(Transaction.tx_hash).where(Transaction.id == from_id - 1)
        ).scalar_one_or_none()
        expected_prev = prev_row or GENESIS_PREV_HASH

    leaves: list[str] = []
    first_invalid_id: int | None = None
    for r in rows:
        payload = json.loads(r.payload_json)
        meta = _meta_for(r)
        recomputed = compute_tx_hash(expected_prev, meta, payload)
        if r.prev_hash != expected_prev or r.tx_hash != recomputed:
            first_invalid_id = r.id
            break
        leaves.append(r.tx_hash)
        expected_prev = r.tx_hash

    return {
        "ok": first_invalid_id is None,
        "count": len(rows),
        "start_id": rows[0].id,
        "end_id": rows[-1].id,
        "first_invalid_id": first_invalid_id,
        "recomputed_root": merkle_root(leaves) if first_invalid_id is None else None,
    }


def rechain_ledger(db: Session) -> dict:
    """남아 있는 트랜잭션들을 id 순서대로 genesis 부터 prev_hash→tx_hash 체인을
    재계산해 무결성을 복구한다.

    트랜잭션을 중간에서 삭제하면(예: 데모 리셋) 이후 행의 prev_hash 가 사라진 해시를
    가리켜 /explorer/verify 가 위반으로 잡는다. 이 함수는 payload 는 건드리지 않고
    체인 링크(prev_hash·tx_hash)만 현재 남은 행들 기준으로 다시 이어 붙인다.
    해시가 전부 바뀌므로 기존 머클 스냅샷은 무효 → 함께 비운다(스냅샷 워커가 재생성).

    append-only 원칙상 평상시 호출 금지. 삭제로 끊긴 체인을 고치는 복구용 도구다.
    """
    from app.db.models.merkle_snapshot import MerkleSnapshot

    rows: list[Transaction] = list(
        db.execute(select(Transaction).order_by(Transaction.id.asc())).scalars()
    )
    # 1단계: tx_hash unique 제약 충돌 방지를 위해 임시 고유값으로 비운다.
    for r in rows:
        r.tx_hash = f"__rechain_tmp_{r.id}"
    db.flush()

    # 2단계: genesis 부터 실제 해시 재계산 (payload 는 보존).
    prev = GENESIS_PREV_HASH
    for r in rows:
        payload = json.loads(r.payload_json)  # _ledger_ts 포함, 그대로 사용
        leaf = compute_tx_hash(prev, {"tx_type": r.tx_type}, payload)
        r.prev_hash = prev
        r.tx_hash = leaf
        prev = leaf
    db.flush()

    # 머클 스냅샷은 옛 해시 기준이라 무효 → 제거(워커가 새 체인으로 재생성).
    snap_deleted = db.query(MerkleSnapshot).delete()
    db.commit()
    return {"rechained": len(rows), "merkle_snapshots_cleared": snap_deleted, "head": prev}


def chain_height(db: Session) -> int:
    return (
        db.execute(select(Transaction.id).order_by(Transaction.id.desc()).limit(1)).scalar_one_or_none()
        or 0
    )


def merkle_root_for_range(db: Session, from_id: int, to_id: int) -> tuple[str, int]:
    rows: Iterable[str] = db.execute(
        select(Transaction.tx_hash)
        .where(Transaction.id >= from_id, Transaction.id <= to_id)
        .order_by(Transaction.id.asc())
    ).scalars()
    leaves = list(rows)
    return merkle_root(leaves), len(leaves)
