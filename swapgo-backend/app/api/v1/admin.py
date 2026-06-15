"""관리자: 자산/풀 추가, 봇 계정/키 발급, 글로서리 시드 리로드."""

from __future__ import annotations

import hashlib
import json
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_admin_token, get_db
from app.db.models.api_key import ApiKey
from app.db.models.asset import Asset
from app.db.models.user import User
from app.schemas.admin import CreateAssetReq, CreateBotReq
from app.schemas.pool import CreatePoolReq
from app.services import pool_service

router = APIRouter(dependencies=[Depends(get_admin_token)])


@router.post("/assets")
def create_asset(req: CreateAssetReq, db: Session = Depends(get_db)):
    existing = db.get(Asset, req.symbol)
    if existing:
        return envelope_ok(
            {"symbol": existing.symbol, "decimals": existing.decimals, "exists": True}
        )
    db.add(
        Asset(symbol=req.symbol, name=req.name, decimals=req.decimals, logo_url=req.logo_url)
    )
    db.commit()
    return envelope_ok({"symbol": req.symbol, "decimals": req.decimals, "exists": False})


@router.post("/pools")
def create_pool(req: CreatePoolReq, db: Session = Depends(get_db)):
    p = pool_service.create_pool(
        db,
        base_symbol=req.base_symbol,
        quote_symbol=req.quote_symbol,
        init_base_human=req.init_base_human,
        init_quote_human=req.init_quote_human,
        fee_bps=req.fee_bps,
    )
    db.commit()
    return envelope_ok(p)


@router.post("/bots")
def create_bot(req: CreateBotReq, db: Session = Depends(get_db)):
    """봇 계정과 API 키를 생성한다. raw key는 응답으로 1회만 노출."""
    bot = User(display_name=req.label, role="bot")
    db.add(bot)
    db.flush()

    raw = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    api_key = ApiKey(
        user_id=bot.id,
        key_hash=key_hash,
        scopes=json.dumps(req.scopes),
        label=req.label,
    )
    db.add(api_key)
    db.commit()

    return envelope_ok(
        {
            "user_id": bot.id,
            "api_key_ONCE": raw,
            "scopes": req.scopes,
            "warning": "API 키는 이 응답에서만 표시되며 다시 확인할 수 없습니다.",
        }
    )


@router.post("/glossary/reload")
def reload_glossary(db: Session = Depends(get_db)):
    from app.seeders.seed_glossary import GLOSSARY_SEED
    from app.services import glossary_service

    n = glossary_service.upsert_terms(db, terms=GLOSSARY_SEED)
    return envelope_ok({"upserted": n})


@router.post("/seed")
def bootstrap_seed(db: Session = Depends(get_db)):
    """원클릭 시드: 자산/풀/글로서리/봇 한 번에 준비."""
    from app.seeders import seed_pools, seed_glossary, seed_bot

    seed_pools.run(db)
    seed_glossary.run(db)
    bot_info = seed_bot.run(db)
    return envelope_ok({"glossary": "seeded", "pools": "seeded", "bot": bot_info})
