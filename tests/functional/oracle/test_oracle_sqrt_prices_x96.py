import pytest

from utils.constants import TICK_CUMULATIVE_RATE_MAX


@pytest.mark.parametrize("pool_greater_than_oracle", [True, False])
def test_oracle_sqrt_prices_x96__returns_prices(
    oracle_lens,
    initializer,
    pool_initialized_with_liquidity,
    mock_univ3_pool,
    oracle_sqrt_price_initial_x96,
    sender,
    chain,
    pool_greater_than_oracle,
):
    # initialize sqrt price to 1% higher than oracle pool
    slot0 = mock_univ3_pool.slot0()
    sqrt_price_x96_next = (
        (slot0.sqrtPriceX96 * 101) // 100
        if pool_greater_than_oracle
        else (slot0.sqrtPriceX96 * 99) // 100
    )

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        sender.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    state = pool_initialized_with_liquidity.state()
    assert pytest.approx(state.sqrtPriceX96, rel=2e-4) == sqrt_price_x96_next

    pool_key = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
    )
    result = oracle_lens.sqrtPricesX96(pool_key)

    sqrt_price_x96 = state.sqrtPriceX96
    oracle_sqrt_price_x96 = oracle_sqrt_price_initial_x96

    delta = state.tick - slot0.tick
    assert abs(delta) < TICK_CUMULATIVE_RATE_MAX
    funding_ratio_x96 = int((1.0001 ** (delta)) * (1 << 96))

    assert result.sqrtPriceX96 == sqrt_price_x96
    assert result.oracleSqrtPriceX96 == oracle_sqrt_price_x96
    assert pytest.approx(result.fundingRatioX96, rel=1e-6) == funding_ratio_x96


@pytest.mark.parametrize("pool_greater_than_oracle", [True, False])
def test_oracle_sqrt_prices_x96__clamps_funding_ratio(
    oracle_lens,
    initializer,
    pool_initialized_with_liquidity,
    mock_univ3_pool,
    oracle_sqrt_price_initial_x96,
    sender,
    chain,
    pool_greater_than_oracle,
):
    # initialize sqrt price to 11% higher than oracle pool
    slot0 = mock_univ3_pool.slot0()
    sqrt_price_x96_next = (
        (slot0.sqrtPriceX96 * 111) // 100
        if pool_greater_than_oracle
        else (slot0.sqrtPriceX96 * 89) // 100
    )

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        sender.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    state = pool_initialized_with_liquidity.state()
    assert pytest.approx(state.sqrtPriceX96, rel=2e-4) == sqrt_price_x96_next

    pool_key = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
    )
    result = oracle_lens.sqrtPricesX96(pool_key)

    sqrt_price_x96 = state.sqrtPriceX96
    oracle_sqrt_price_x96 = oracle_sqrt_price_initial_x96

    delta = state.tick - slot0.tick
    assert abs(delta) > TICK_CUMULATIVE_RATE_MAX
    delta = TICK_CUMULATIVE_RATE_MAX if delta > 0 else -TICK_CUMULATIVE_RATE_MAX
    funding_ratio_x96 = int((1.0001 ** (delta)) * (1 << 96))

    assert result.sqrtPriceX96 == sqrt_price_x96
    assert result.oracleSqrtPriceX96 == oracle_sqrt_price_x96
    assert pytest.approx(result.fundingRatioX96, rel=1e-6) == funding_ratio_x96
