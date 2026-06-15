"""용어사전 조회 + 시드 데이터 로더."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.glossary_term import GlossaryTerm


def to_dict(t: GlossaryTerm) -> dict:
    related = json.loads(t.related_keys) if t.related_keys else []
    return {
        "key": t.key,
        "term_ko": t.term_ko,
        "term_en": t.term_en,
        "short_desc": t.short_desc,
        "long_desc": t.long_desc,
        "example": t.example,
        "related_keys": related,
        "difficulty": t.difficulty,
    }


def list_all(db: Session) -> list[dict]:
    rows = list(db.execute(select(GlossaryTerm).order_by(GlossaryTerm.key.asc())).scalars())
    return [to_dict(r) for r in rows]


def get(db: Session, *, key: str) -> dict | None:
    r = db.get(GlossaryTerm, key)
    return to_dict(r) if r else None


def search(db: Session, *, q: str) -> list[dict]:
    pattern = f"%{q}%"
    rows = list(
        db.execute(
            select(GlossaryTerm).where(
                or_(
                    GlossaryTerm.term_ko.ilike(pattern),
                    GlossaryTerm.term_en.ilike(pattern),
                    GlossaryTerm.key.ilike(pattern),
                    GlossaryTerm.short_desc.ilike(pattern),
                )
            )
        ).scalars()
    )
    return [to_dict(r) for r in rows]


def upsert_terms(db: Session, *, terms: list[dict[str, Any]]) -> int:
    n = 0
    for t in terms:
        existing = db.get(GlossaryTerm, t["key"])
        if existing:
            existing.term_ko = t["term_ko"]
            existing.term_en = t.get("term_en")
            existing.short_desc = t["short_desc"]
            existing.long_desc = t.get("long_desc")
            existing.example = t.get("example")
            existing.related_keys = json.dumps(t.get("related_keys", []), ensure_ascii=False)
            existing.difficulty = int(t.get("difficulty", 1))
        else:
            db.add(
                GlossaryTerm(
                    key=t["key"],
                    term_ko=t["term_ko"],
                    term_en=t.get("term_en"),
                    short_desc=t["short_desc"],
                    long_desc=t.get("long_desc"),
                    example=t.get("example"),
                    related_keys=json.dumps(t.get("related_keys", []), ensure_ascii=False),
                    difficulty=int(t.get("difficulty", 1)),
                )
            )
        n += 1
    db.commit()
    return n
