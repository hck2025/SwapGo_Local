from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import envelope_ok
from app.deps import get_db
from app.schemas.auth import (
    ChallengeReq,
    LoginReq,
    SignupReq,
)
from app.services import auth_service

router = APIRouter()


@router.post("/signup")
def signup(req: SignupReq, db: Session = Depends(get_db)):
    data = auth_service.signup(db, display_name=req.display_name)
    return envelope_ok(
        {
            "address": data["address"],
            "public_key_hex": data["public_key_hex"],
            "private_key_ONCE": data["private_key_ONCE"],
            "mnemonic_ONCE": data["mnemonic_ONCE"],
            "warning": (
                "이 화면을 벗어나면 개인키와 니모닉은 다시 표시되지 않아요. "
                "안전한 곳에 보관하지 않으면 계정 복구가 불가능합니다."
            ),
            "glossary_keys": ["wallet", "private_key", "mnemonic"],
        }
    )


@router.post("/challenge")
def challenge(req: ChallengeReq, db: Session = Depends(get_db)):
    data = auth_service.issue_challenge(db, address=req.address)
    return envelope_ok(data)


@router.post("/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    data = auth_service.verify_login(
        db, address=req.address, signature_hex=req.signature, nonce=req.nonce
    )
    return envelope_ok(data)


@router.post("/logout")
def logout():
    # JWT는 stateless. 클라가 토큰 폐기하면 끝.
    return envelope_ok({"message": "로그아웃되었어요."})
