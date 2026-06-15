from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db
from app.services import pool_service

router = APIRouter()


@router.get("")
def list_pools(only_active: bool = Query(default=False), db: Session = Depends(get_db)):
    return envelope_ok(pool_service.list_pools(db, only_active=only_active))


@router.get("/{pool_id}")
def get_pool(pool_id: int, db: Session = Depends(get_db)):
    p = pool_service.get_pool(db, pool_id)
    return envelope_ok(pool_service.pool_to_dict(db, p))
