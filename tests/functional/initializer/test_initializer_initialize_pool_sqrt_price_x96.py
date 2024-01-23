import pytest

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_LIQUIDITY


def test_initializer_initialize_pool_sqrt_price_x96__sets_to_sqrt_price_x96(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )

    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    # TODO: fix for fees in contract?
    result = pool.state()
    assert pytest.approx(result.sqrtPriceX96, rel=1e-4) == slot0.sqrtPriceX96
