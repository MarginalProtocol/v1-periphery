import pytest

from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_exact_output_single__quotes_swap(
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

    # cache balance of token out prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

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

    # quote first before state change
    result = quoter.quoteExactOutputSingle(params)

    # actually swap and check result same as quote
    router.exactOutputSingle(params, sender=sender)

    amount_in = (
        balance0_sender - token0.balanceOf(sender.address)
        if zero_for_one
        else balance1_sender - token1.balanceOf(sender.address)
    )
    assert result.amountIn == amount_in

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96
