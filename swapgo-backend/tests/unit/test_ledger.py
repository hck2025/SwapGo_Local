from app.db.base import SessionLocal
from app.db.models.transaction import Transaction
from app.services.ledger_service import append_tx, verify_chain


def test_chain_append_and_verify():
    db = SessionLocal()
    try:
        # 깨끗한 상태에서 시작
        db.query(Transaction).delete()
        db.commit()

        for i in range(5):
            append_tx(
                db,
                tx_type="test",
                payload={"i": i, "x": "abc"},
            )
            db.commit()

        result = verify_chain(db)
        assert result["ok"] is True
        assert result["count"] == 5
        assert result["first_invalid_id"] is None
    finally:
        db.close()


def test_chain_detects_tamper():
    db = SessionLocal()
    try:
        db.query(Transaction).delete()
        db.commit()

        for i in range(3):
            append_tx(db, tx_type="t", payload={"i": i})
            db.commit()

        # 가운데 행의 payload를 변조
        row = db.query(Transaction).order_by(Transaction.id.asc()).all()[1]
        row.payload_json = '{"i":99}'
        db.commit()

        result = verify_chain(db)
        assert result["ok"] is False
        assert result["first_invalid_id"] == row.id
    finally:
        db.close()
