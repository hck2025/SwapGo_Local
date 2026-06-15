"""회원가입(키쌍 발급), 로그인 챌린지/검증.

- 회원가입: 서버가 secp256k1 키쌍 + BIP39 니모닉을 생성하여 응답으로 1회만 노출.
  서버는 공개키와 주소만 저장한다 (개인키/니모닉은 어떤 형태로도 저장 금지).
- 로그인: 챌린지 nonce → EIP-191 personal_sign 서명 → 공개키 복원으로 주소 매칭.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import crypto, mnemonic
from app.core.errors import (
    InvalidSignature,
    NonceAlreadyUsed,
    NonceExpired,
    WalletNotFound,
)
from app.core.security import create_access_token
from app.core.time import iso_now, kst_now
from app.db.models.nonce import Nonce
from app.db.models.user import User
from app.db.models.wallet import Wallet


_NONCE_TTL = timedelta(minutes=5)


def signup(db: Session, *, display_name: str | None = None) -> dict:
    priv, pub_compressed, address = crypto.generate_keypair()
    words = mnemonic.generate_mnemonic_words()

    user = User(display_name=display_name, role="user")
    db.add(user)
    db.flush()
    wallet = Wallet(user_id=user.id, public_key=pub_compressed, address=address)
    db.add(wallet)
    db.flush()
    db.commit()

    return {
        "address": address,
        "public_key_hex": "0x" + pub_compressed.hex(),
        "private_key_ONCE": "0x" + priv.hex(),
        "mnemonic_ONCE": words,
    }


def issue_challenge(db: Session, *, address: str) -> dict:
    wallet = db.execute(
        select(Wallet).where(Wallet.address == address)
    ).scalar_one_or_none()
    if wallet is None:
        raise WalletNotFound()

    nonce = secrets.token_hex(16)
    issued = kst_now()
    expires = issued + _NONCE_TTL
    message = f"SwapGo Login: {nonce} at {issued.isoformat()}"

    db.add(
        Nonce(
            address=address,
            nonce=nonce,
            message=message,
            issued_at=issued,
            expires_at=expires,
            used=False,
        )
    )
    db.commit()

    return {"nonce": nonce, "message": message, "expires_at": expires.isoformat()}


def verify_login(
    db: Session,
    *,
    address: str,
    signature_hex: str,
    nonce: str,
) -> dict:
    nonce_row = db.execute(
        select(Nonce).where(Nonce.nonce == nonce, Nonce.address == address)
    ).scalar_one_or_none()
    if nonce_row is None:
        raise NonceExpired()
    if nonce_row.used:
        raise NonceAlreadyUsed()
    expires_aware = nonce_row.expires_at
    if expires_aware.tzinfo is None:
        expires_aware = expires_aware.replace(tzinfo=kst_now().tzinfo)
    if expires_aware < kst_now():
        raise NonceExpired()

    if not crypto.verify_signature(nonce_row.message, signature_hex, address):
        raise InvalidSignature()

    nonce_row.used = True

    wallet = db.execute(
        select(Wallet).where(Wallet.address == address)
    ).scalar_one_or_none()
    if wallet is None:
        raise WalletNotFound()
    user = db.get(User, wallet.user_id)

    token, expires_in = create_access_token(
        subject=str(user.id), address=address, role=user.role
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "address": address,
        "issued_at": iso_now(),
    }
