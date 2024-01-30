import pytest


def test_arbitrageur_execute__executes_arbitrage_with_marginal_price_higher_token_out_zero(
    arbitrageur,
    spot_pool_initialized_with_liquidity,
    pool_initialized_with_liquidity,
    token0,
    token1,
    sender,
    alice,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()
    assert state.sqrtPriceX96 > slot0.sqrtPriceX96

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price > Uniswap price, so should take route:
    # 0 => Marginal => 1 => Uniswap => 0
    token_out = pool_initialized_with_liquidity.token0()
    amount_out_min = 0
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    deadline = chain.pending_timestamp + 3600
    sweep_as_eth = False

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    arbitrageur.execute(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    slot0_after = spot_pool_initialized_with_liquidity.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = token0.balanceOf(alice.address)
    balance1_alice_after = token1.balanceOf(alice.address)
    assert balance0_alice_after > 0
    assert balance1_alice_after == 0


def test_arbitrageur_execute__executes_arbitrage_with_marginal_price_higher_token_out_one(
    arbitrageur,
    spot_pool_initialized_with_liquidity,
    pool_initialized_with_liquidity,
    token0,
    token1,
    sender,
    alice,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()
    assert state.sqrtPriceX96 > slot0.sqrtPriceX96

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price > Uniswap price, so should take route:
    # 1 => Uniswap => 0 => Marginal => 1
    token_out = pool_initialized_with_liquidity.token1()
    amount_out_min = 0
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    deadline = chain.pending_timestamp + 3600
    sweep_as_eth = False

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    arbitrageur.execute(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    slot0_after = spot_pool_initialized_with_liquidity.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = token0.balanceOf(alice.address)
    balance1_alice_after = token1.balanceOf(alice.address)
    assert balance0_alice_after == 0
    assert balance1_alice_after > 0


def test_arbitrageur_execute__executes_arbitrage_with_marginal_price_lower_token_out_zero(
    arbitrageur,
    initializer,
    spot_pool_initialized_with_liquidity,
    pool_initialized_with_liquidity,
    token0,
    token1,
    sender,
    alice,
    chain,
):
    # execute a swap through initializer to move marginal pool price below uniswap oracle price
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()

    # move price on marginal pool to below uni price for test of less than sqrt price
    sqrt_price_x96_next = (slot0.sqrtPriceX96**2) // state.sqrtPriceX96
    assert sqrt_price_x96_next < slot0.sqrtPriceX96

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

    # check price now below
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()
    assert state.sqrtPriceX96 < slot0.sqrtPriceX96

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price < Uniswap price, so should take route:
    # 0 => Uniswap => 1 => Marginal => 0
    token_out = pool_initialized_with_liquidity.token0()
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    sweep_as_eth = False

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    arbitrageur.execute(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    slot0_after = spot_pool_initialized_with_liquidity.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = token0.balanceOf(alice.address)
    balance1_alice_after = token1.balanceOf(alice.address)
    assert balance0_alice_after > 0
    assert balance1_alice_after == 0


def test_arbitrageur_execute__executes_arbitrage_with_marginal_price_lower_token_out_one(
    arbitrageur,
    initializer,
    spot_pool_initialized_with_liquidity,
    pool_initialized_with_liquidity,
    token0,
    token1,
    sender,
    alice,
    chain,
):
    # execute a swap through initializer to move marginal pool price below uniswap oracle price
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()

    # move price on marginal pool to below uni price for test of less than sqrt price
    sqrt_price_x96_next = (slot0.sqrtPriceX96**2) // state.sqrtPriceX96
    assert sqrt_price_x96_next < slot0.sqrtPriceX96

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

    # check price now below
    state = pool_initialized_with_liquidity.state()
    slot0 = spot_pool_initialized_with_liquidity.slot0()
    assert state.sqrtPriceX96 < slot0.sqrtPriceX96

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price < Uniswap price, so should take route:
    # 1 => Marginal => 0 => Uniswap => 1
    token_out = pool_initialized_with_liquidity.token1()
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    sweep_as_eth = False

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    arbitrageur.execute(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    slot0_after = spot_pool_initialized_with_liquidity.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = token0.balanceOf(alice.address)
    balance1_alice_after = token1.balanceOf(alice.address)
    assert balance0_alice_after == 0
    assert balance1_alice_after > 0
