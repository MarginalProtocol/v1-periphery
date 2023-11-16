import pytest

# from ape import reverts
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__updates_state(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    router.exactOutputSingle(params, sender=sender)

    # calculate liquidity, sqrtPriceX96 update
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee)
        amount1 += fees1

    # determine liquidity, sqrtPriceX96 after
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )
    tick_after = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == liquidity_after
    assert result.sqrtPriceX96 == sqrt_price_x96_after
    assert result.tick == tick_after


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__transfers_funds(
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__returns_amount_out(
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__reverts_when_past_deadline(
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__reverts_when_amount_in_greater_than_max(
    zero_for_one,
):
    pass
