"""주기적으로 머클루트 스냅샷을 저장한다.

주기: MERKLE_SNAPSHOT_INTERVAL_SEC 또는 신규 거래가 MERKLE_SNAPSHOT_BATCH 이상 쌓이면.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.db.base import SessionLocal
from app.db.models.merkle_snapshot import MerkleSnapshot
from app.services import ledger_service


async def run_forever(stop_event: asyncio.Event) -> None:
    s = get_settings()
    while not stop_event.is_set():
        try:
            _tick(batch=s.MERKLE_SNAPSHOT_BATCH)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=s.MERKLE_SNAPSHOT_INTERVAL_SEC)
        except asyncio.TimeoutError:
            continue


def _tick(*, batch: int) -> None:
    db = SessionLocal()
    try:
        last = db.execute(
            select(MerkleSnapshot).order_by(MerkleSnapshot.id.desc()).limit(1)
        ).scalar_one_or_none()
        height = ledger_service.chain_height(db)
        from_id = (last.to_tx_id + 1) if last else 1
        if height < from_id:
            return
        if (height - from_id + 1) < batch and last is not None:
            return
        root, count = ledger_service.merkle_root_for_range(db, from_id, height)
        if count == 0:
            return
        db.add(
            MerkleSnapshot(
                from_tx_id=from_id,
                to_tx_id=height,
                merkle_root=root,
                tx_count=count,
            )
        )
        db.commit()
    finally:
        db.close()
