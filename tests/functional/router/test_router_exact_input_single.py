import pytest

from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__updates_state(
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    # calculate liquidity, sqrtPriceX96 update in slightly diff way than on-chain. check close
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in,
    )  # price change before fees added

    # fees on amount in
    fees = swap_math_lib.swapFees(amount_in, fee)
    amount0 = fees if zero_for_one else 0
    amount1 = 0 if zero_for_one else fees

    (liquidity_after, sqrt_price_x96_after) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        sqrt_price_x96_next,
        amount0,
        amount1
    )

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == liquidity_after
    assert result.sqrtPriceX96 == sqrt_price_x96_after


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__transfers_funds(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__returns_amount_out(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__reverts_when_amount_out_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
):
    pass
