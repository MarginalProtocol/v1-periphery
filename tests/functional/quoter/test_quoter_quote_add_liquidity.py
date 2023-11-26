def test_quoter_quote_add_liquidity__quotes_liquidity_add(
    pool_initialized_with_liquidity,
    quoter,
    router,
    manager,
    sender,
    alice,
    chain,
    token0,
    token1,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    # cache balances of tokens prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteAddLiquidity(params)

    # actually add liquidity and check result same as quote
    router.addLiquidity(params, sender=sender)

    shares = pool_initialized_with_liquidity.balanceOf(alice.address) - shares_alice
    assert result.shares == shares

    amount0 = balance0_sender - token0.balanceOf(sender.address)
    amount1 = balance1_sender - token1.balanceOf(sender.address)
    assert result.amount0 == amount0
    assert result.amount1 == amount1

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity


# TODO: test revert statements
