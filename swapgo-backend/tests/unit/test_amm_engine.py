import pytest

from app.core.errors import InsufficientLiquidity, InvalidAmount
from app.services.amm_engine import (
    auto_slippage_tolerance_bps,
    classify_slippage,
    initial_lp_shares,
    quote_swap,
)


def test_quote_basic_uniswap_v2_equivalence():
    # Uniswap V2 공식 등가성: amount_out = (in*9970*r_out)/(r_in*10000+in*9970)
    r_in = 100_000_000
    r_out = 200_000_000
    amount_in = 1_000_000

    q = quote_swap(r_in, r_out, amount_in, fee_bps=30)

    expected = (amount_in * 9970 * r_out) // (r_in * 10000 + amount_in * 9970)
    assert q.amount_out == expected
    assert q.fee_amount == amount_in * 30 // 10000
    assert q.new_reserve_in == r_in + amount_in
    assert q.new_reserve_out == r_out - q.amount_out


def test_quote_zero_reserves_raises():
    with pytest.raises(InsufficientLiquidity):
        quote_swap(0, 100, 10)


def test_quote_zero_amount_raises():
    with pytest.raises(InvalidAmount):
        quote_swap(100, 100, 0)


def test_k_monotonically_increases_with_fee():
    # 수수료가 누적되면 x*y=k 가 거래 후 약간 증가해야 한다 (Uniswap V2 invariant 강화)
    r_in = 1_000_000_000
    r_out = 5_000_000_000
    k_before = r_in * r_out
    q = quote_swap(r_in, r_out, 10_000_000, fee_bps=30)
    k_after = q.new_reserve_in * q.new_reserve_out
    assert k_after >= k_before


def test_classify_slippage_thresholds():
    assert classify_slippage(0) == "safe"
    assert classify_slippage(49) == "safe"
    assert classify_slippage(50) == "warning"
    assert classify_slippage(299) == "warning"
    assert classify_slippage(300) == "danger"
    assert classify_slippage(1000) == "danger"


def test_auto_slippage_floor_and_scale():
    assert auto_slippage_tolerance_bps(0) == 50  # floor
    assert auto_slippage_tolerance_bps(100) >= 150  # 1.5x
    assert auto_slippage_tolerance_bps(1000) >= 1500


def test_initial_lp_shares_geometric_mean():
    s = initial_lp_shares(100_000_000, 4_000_000_000)
    # sqrt(100e6 * 4e9) = sqrt(4e17) = 2e8.5 → 632455532
    assert 632_000_000 < s < 633_000_000
