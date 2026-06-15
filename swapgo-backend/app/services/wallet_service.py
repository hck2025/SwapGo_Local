"""모의 입출금/잔고 조회. 입출금은 ledger에 기록되어 익스플로러에 노출된다."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.amount import to_base_units, to_human
from app.core.errors import InsufficientBalance, InvalidAmount
from app.db.models.asset import Asset
from app.db.models.balance import Balance
from app.db.models.wallet import Wallet
from app.services import ledger_service


def _get_or_create_balance(db: Session, *, wallet_id: int, symbol: str) -> Balance:
    bal = db.execute(
        select(Balance).where(Balance.wallet_id == wallet_id, Balance.asset_symbol == symbol)
    ).scalar_one_or_none()
    if bal is None:
        bal = Balance(wallet_id=wallet_id, asset_symbol=symbol, amount=0)
        db.add(bal)
        db.flush()
    return bal


def list_balances(db: Session, *, wallet_id: int) -> list[dict]:
    rows = db.execute(
        select(Balance, Asset)
        .join(Asset, Asset.symbol == Balance.asset_symbol)
        .where(Balance.wallet_id == wallet_id)
    ).all()
    out: list[dict] = []
    for bal, asset in rows:
        out.append(
            {
                "symbol": asset.symbol,
                "amount": str(int(bal.amount or 0)),
                "amount_human": to_human(int(bal.amount or 0), asset.decimals),
                "decimals": asset.decimals,
            }
        )
    return out


def deposit_mock(
    db: Session,
    *,
    wallet: Wallet,
    symbol: str,
    amount_human: str,
) -> dict:
    asset = db.get(Asset, symbol)
    if asset is None:
        raise InvalidAmount(f"지원하지 않는 자산: {symbol}")
    amount = to_base_units(amount_human, asset.decimals)
    if amount <= 0:
        raise InvalidAmount()

    bal = _get_or_create_balance(db, wallet_id=wallet.id, symbol=symbol)
    bal.amount = int(bal.amount or 0) + amount

    payload = {
        "actor_address": wallet.address,
        "symbol": symbol,
        "amount": str(amount),
        "balance_after": str(int(bal.amount)),
    }
    appended = ledger_service.append_tx(
        db,
        tx_type="deposit",
        payload=payload,
        actor_wallet_id=wallet.id,
        amount_in=amount,
    )
    db.commit()
    return {
        "tx_id": appended.tx_id,
        "tx_hash": appended.tx_hash,
        "new_balance": str(int(bal.amount)),
        "new_balance_human": to_human(int(bal.amount), asset.decimals),
    }


def withdraw_mock(
    db: Session,
    *,
    wallet: Wallet,
    symbol: str,
    amount_human: str,
    to_address: str,
) -> dict:
    asset = db.get(Asset, symbol)
    if asset is None:
        raise InvalidAmount(f"지원하지 않는 자산: {symbol}")
    amount = to_base_units(amount_human, asset.decimals)
    if amount <= 0:
        raise InvalidAmount()

    bal = _get_or_create_balance(db, wallet_id=wallet.id, symbol=symbol)
    if int(bal.amount or 0) < amount:
        raise InsufficientBalance()
    bal.amount = int(bal.amount) - amount

    payload = {
        "actor_address": wallet.address,
        "to_address": to_address,
        "symbol": symbol,
        "amount": str(amount),
        "balance_after": str(int(bal.amount)),
    }
    appended = ledger_service.append_tx(
        db,
        tx_type="withdraw",
        payload=payload,
        actor_wallet_id=wallet.id,
        amount_out=amount,
    )
    db.commit()
    return {
        "tx_id": appended.tx_id,
        "tx_hash": appended.tx_hash,
        "new_balance": str(int(bal.amount)),
        "new_balance_human": to_human(int(bal.amount), asset.decimals),
    }
