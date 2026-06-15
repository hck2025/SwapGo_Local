from app.services.orderbook_synth import synth_orderbook


def test_orderbook_monotonic_levels():
    book = synth_orderbook(100_000_000, 4_325_000_000_000, fee_bps=30, levels=10, step_pct=0.001)
    assert len(book["asks"]) > 0
    assert len(book["bids"]) > 0
    asks = [(l["price_raw"], l["cum_base_raw"]) for l in book["asks"]]
    for (p1, c1), (p2, c2) in zip(asks, asks[1:]):
        assert p2 > p1
        assert c2 >= c1
    bids = [(l["price_raw"], l["cum_base_raw"]) for l in book["bids"]]
    for (p1, c1), (p2, c2) in zip(bids, bids[1:]):
        assert p2 < p1
        assert c2 >= c1


def test_orderbook_empty_pool():
    out = synth_orderbook(0, 0)
    assert out["asks"] == []
    assert out["bids"] == []
