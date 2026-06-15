def test_glossary_seeded(client):
    client.post("/admin/seed", headers={"x-admin-token": "test-admin"})
    r = client.get("/glossary")
    assert r.status_code == 200
    keys = {it["key"] for it in r.json()["data"]["items"]}
    assert {"slippage", "amm", "cpmm", "liquidity_pool"} <= keys


def test_explorer_public_no_auth(client):
    client.post("/admin/seed", headers={"x-admin-token": "test-admin"})
    r = client.get("/explorer/blocks?from=1")
    assert r.status_code == 200


def test_glossary_term_lookup(client):
    client.post("/admin/seed", headers={"x-admin-token": "test-admin"})
    r = client.get("/glossary/slippage")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["term_ko"] == "슬리피지"
