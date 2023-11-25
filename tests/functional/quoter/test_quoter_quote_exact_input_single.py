import pytest

from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_exact_input_single__quotes_swap(
    pool_initialized_with_liquidity,
    quoter,
    router,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # cache balance of token out prior
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )

    # quote first before state change
    result = quoter.quoteExactInputSingle(params)

    # actually swap and check result same as quote
    router.exactInputSingle(params, sender=sender)

    amount_out = (
        token1.balanceOf(alice.address) - balance1_alice
        if zero_for_one
        else token0.balanceOf(alice.address) - balance0_alice
    )
    assert result.amountOut == amount_out

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96


# TODO: test revert statements
