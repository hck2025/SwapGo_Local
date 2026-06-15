"""핵심 E2E: 회원가입 → 챌린지 → 로그인 → 입금 → 견적 → 실행 → 익스플로러 검증."""

from __future__ import annotations

from app.core.crypto import sign_message


def _signup_login(client) -> tuple[str, str]:
    r = client.post("/auth/signup", json={"display_name": "alice"})
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    address = body["address"]
    priv_hex = body["private_key_ONCE"][2:]

    r = client.post("/auth/challenge", json={"address": address})
    assert r.status_code == 200
    nonce = r.json()["data"]["nonce"]
    message = r.json()["data"]["message"]

    sig = sign_message(bytes.fromhex(priv_hex), message)
    r = client.post(
        "/auth/login",
        json={"address": address, "signature": "0x" + sig.hex(), "nonce": nonce},
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return address, token


def _ensure_seed(client):
    client.post("/admin/seed", headers={"x-admin-token": "test-admin"})


def test_full_flow(client):
    _ensure_seed(client)
    addr, token = _signup_login(client)
    auth = {"Authorization": f"Bearer {token}"}

    # 모의 입금
    r = client.post(
        "/wallet/deposit/mock",
        json={"symbol": "USDT", "amount": "100000"},
        headers=auth,
    )
    assert r.status_code == 200, r.text

    # 풀 1번이 BTC/USDT 라고 가정 (시드 순서)
    pools = client.get("/pools").json()["data"]
    btc_pool = next(p for p in pools if p["base_symbol"] == "BTC")

    # 견적
    r = client.post(
        "/swap/quote",
        json={
            "pool_id": btc_pool["id"],
            "side": "quote_to_base",  # USDT → BTC
            "amount_in_human": "100",
        },
    )
    body = r.json()
    assert r.status_code == 200, body
    quote = body["data"]
    assert quote["slippage_level"] in ("safe", "warning", "danger")
    assert "friendly_message" in quote
    assert "slippage" in quote["glossary_keys"]

    # 실행
    r = client.post(
        "/swap/execute",
        json={
            "pool_id": btc_pool["id"],
            "side": "quote_to_base",
            "amount_in_human": "100",
            "min_amount_out": quote["amount_out_min"],
            "slippage_tolerance_bps": quote["slippage_threshold_used_bps"],
        },
        headers=auth,
    )
    body = r.json()
    assert r.status_code == 200, body
    tx_hash = body["data"]["tx_hash"]
    tx_id = body["data"]["tx_id"]
    assert tx_hash and tx_id > 0

    # 거래내역 확인
    r = client.get("/me/transactions", headers=auth)
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert any(it["tx_hash"] == tx_hash for it in items)

    # 익스플로러 (인증 불필요)
    r = client.get(f"/explorer/tx/{tx_id}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["tx_hash"] == tx_hash
    assert data["actor_address"] == addr

    # 검증
    r = client.get(f"/explorer/verify?from=1&to={tx_id}")
    assert r.json()["data"]["ok"] is True


def test_slippage_exceeded_returns_friendly_error(client):
    _ensure_seed(client)
    _, token = _signup_login(client)
    auth = {"Authorization": f"Bearer {token}"}

    client.post(
        "/wallet/deposit/mock",
        json={"symbol": "USDT", "amount": "1000000"},
        headers=auth,
    )
    pools = client.get("/pools").json()["data"]
    btc_pool = next(p for p in pools if p["base_symbol"] == "BTC")

    # 풀 대비 매우 큰 거래 + 매우 좁은 허용치 → 거부 기대
    r = client.post(
        "/swap/execute",
        json={
            "pool_id": btc_pool["id"],
            "side": "quote_to_base",
            "amount_in_human": "500000",
            "min_amount_out": "999999999999",  # 사실상 불가능한 최소 출력
            "slippage_tolerance_bps": 10,
        },
        headers=auth,
    )
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "SLIPPAGE_EXCEEDED"
    assert "허용치" in err["message"] or "허용치" in err["suggestion"]
    assert "slippage" in err["glossary_keys"]
