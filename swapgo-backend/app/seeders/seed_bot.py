"""기본 봇 계정 + 키 생성. 라우터 admin과 별도로 부트스트랩에서 사용."""

import hashlib
import json
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import crypto
from app.db.models.api_key import ApiKey
from app.db.models.user import User
from app.db.models.wallet import Wallet


def run(db: Session) -> dict:
    bot = db.execute(select(User).where(User.role == "bot")).scalar_one_or_none()
    if bot is None:
        bot = User(display_name="default-bot", role="bot")
        db.add(bot)
        db.flush()
        priv, pub, addr = crypto.generate_keypair()
        db.add(Wallet(user_id=bot.id, public_key=pub, address=addr))
        db.flush()

    existing = db.execute(
        select(ApiKey).where(ApiKey.user_id == bot.id, ApiKey.revoked_at.is_(None))
    ).scalar_one_or_none()
    if existing:
        db.commit()
        return {
            "user_id": bot.id,
            "api_key_ONCE": None,
            "note": "이미 발급된 봇 키가 있어요. 새로 만들려면 admin/bots를 사용하세요.",
        }

    raw = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    db.add(
        ApiKey(
            user_id=bot.id,
            key_hash=key_hash,
            scopes=json.dumps(["bot:trade", "bot:lp", "bot:ingest"]),
            label="default-bot",
        )
    )
    db.commit()
    return {
        "user_id": bot.id,
        "api_key_ONCE": raw,
        "scopes": ["bot:trade", "bot:lp", "bot:ingest"],
    }
