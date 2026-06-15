from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import envelope_err, envelope_ok
from app.deps import get_db
from app.services import glossary_service

router = APIRouter()


@router.get("")
def list_terms(db: Session = Depends(get_db)):
    return envelope_ok({"items": glossary_service.list_all(db)})


@router.get("/search")
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    return envelope_ok({"items": glossary_service.search(db, q=q)})


@router.get("/{key}")
def get_term(key: str, db: Session = Depends(get_db)):
    item = glossary_service.get(db, key=key)
    if item is None:
        return envelope_err("NOT_FOUND", "해당 용어를 찾지 못했어요.", status_code=404)
    return envelope_ok(item)
