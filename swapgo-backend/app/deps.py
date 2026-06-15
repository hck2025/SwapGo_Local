"""DI 의존성: DB 세션, 현재 사용자(JWT), 봇 인증, 관리자 인증."""

from __future__ import annotations

import hashlib
import json
from typing import Iterator

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.db.base import SessionLocal
from app.db.models.api_key import ApiKey
from app.db.models.user import User
from app.db.models.wallet import Wallet


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _bearer(token_header: str | None) -> str:
    if not token_header:
        raise Unauthorized()
    parts = token_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise Unauthorized("Authorization 헤더 형식이 올바르지 않아요.")
    return parts[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> tuple[User, Wallet]:
    token = _bearer(authorization)
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise Unauthorized("토큰이 만료되었어요.")
    except jwt.PyJWTError:
        raise Unauthorized("토큰이 올바르지 않아요.")

    user_id = int(payload.get("sub", 0))
    user = db.get(User, user_id)
    if user is None:
        raise Unauthorized()
    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    ).scalar_one_or_none()
    if wallet is None:
        raise Unauthorized()
    return user, wallet


def _resolve_bot(db: Session, raw: str) -> tuple[User, list[str]]:
    """raw 봇 키 → (봇 User, scopes). 유효하지 않으면 예외."""
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    api_key = db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
    ).scalar_one_or_none()
    if api_key is None:
        raise Unauthorized("봇 API 키가 유효하지 않아요.")
    user = db.get(User, api_key.user_id)
    if user is None or user.role != "bot":
        raise Forbidden()
    return user, json.loads(api_key.scopes or "[]")


def _wallet_of(db: Session, user: User) -> Wallet:
    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    ).scalar_one_or_none()
    if wallet is None:
        raise Unauthorized("지갑을 찾을 수 없어요.")
    return wallet


def get_current_bot(
    request: Request,
    x_bot_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    raw = x_bot_key
    if not raw and authorization:
        try:
            raw = _bearer(authorization)
        except Unauthorized:
            raw = None
    if not raw:
        raise Unauthorized("봇 API 키가 필요해요.")
    user, scopes = _resolve_bot(db, raw)
    request.state.bot_scopes = scopes
    return user


def require_scope(scope: str):
    def _dep(request: Request, _: User = Depends(get_current_bot)) -> None:
        scopes = getattr(request.state, "bot_scopes", []) or []
        if scope not in scopes:
            raise Forbidden(f"권한 부족: {scope} 스코프가 필요해요.")

    return _dep


def wallet_actor(required_bot_scope: str | None = None):
    """
    JWT 사용자 또는 봇 키(X-Bot-Key / Authorization: Bearer) 둘 다 받아
    거래 주체의 Wallet 을 돌려주는 의존성 팩토리.

    - 사람 사용자: 기존 JWT 흐름 그대로 (스코프 검사 없음).
    - 봇: required_bot_scope 가 주어지면 해당 스코프를 요구.
    프론트(사용자)와 AI팀 봇이 같은 /swap/execute · /wallet/deposit/mock 를
    공유할 수 있게 한다 (AI_가이드 섹션 4 의 계약과 일치).
    """

    def _dep(
        x_bot_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> Wallet:
        # 1) 봇 키 우선 (명시적 X-Bot-Key 헤더)
        if x_bot_key:
            user, scopes = _resolve_bot(db, x_bot_key)
            if required_bot_scope and required_bot_scope not in scopes:
                raise Forbidden(f"권한 부족: {required_bot_scope} 스코프가 필요해요.")
            return _wallet_of(db, user)

        # 2) Authorization: Bearer — JWT(사람) 우선, 실패하면 봇 raw 키로 시도
        if authorization:
            token = _bearer(authorization)
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                raise Unauthorized("토큰이 만료되었어요.")
            except jwt.PyJWTError:
                user, scopes = _resolve_bot(db, token)  # 봇 raw 키
                if required_bot_scope and required_bot_scope not in scopes:
                    raise Forbidden(f"권한 부족: {required_bot_scope} 스코프가 필요해요.")
                return _wallet_of(db, user)
            user_id = int(payload.get("sub", 0))
            user = db.get(User, user_id)
            if user is None:
                raise Unauthorized()
            return _wallet_of(db, user)

        raise Unauthorized("인증이 필요해요.")

    return _dep


def get_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    s = get_settings()
    if not x_admin_token or x_admin_token != s.ADMIN_BOOTSTRAP_TOKEN:
        raise Forbidden("관리자 토큰이 필요해요.")
