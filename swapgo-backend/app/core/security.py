from datetime import timedelta

import jwt

from app.config import get_settings
from app.core.time import kst_now


def create_access_token(*, subject: str, address: str, role: str = "user") -> tuple[str, int]:
    s = get_settings()
    expires_in = s.JWT_EXPIRE_MINUTES * 60
    now = kst_now()
    payload = {
        "sub": subject,
        "addr": address,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, s.JWT_SECRET, algorithm=s.JWT_ALG)
    return token, expires_in


def decode_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALG])
