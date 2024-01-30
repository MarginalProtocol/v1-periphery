import pytest


@pytest.fixture
def mrglv1_pool_initialized_with_liquidity_price_higher(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_initializer,
    univ3_pool,
    sender,
    chain,
):
    slot0 = univ3_pool.slot0()
    sqrt_price_x96_next = slot0.sqrtPriceX96 * 105 // 100

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    params = (
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
        mrglv1_pool_initialized_with_liquidity.maintenance(),
        mrglv1_pool_initialized_with_liquidity.oracle(),
        sender.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    mrglv1_initializer.initializePoolSqrtPriceX96(params, sender=sender)
    return mrglv1_pool_initialized_with_liquidity


@pytest.fixture
def mrglv1_pool_initialized_with_liquidity_price_lower(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_initializer,
    univ3_pool,
    sender,
    chain,
):
    slot0 = univ3_pool.slot0()
    sqrt_price_x96_next = slot0.sqrtPriceX96 * 95 // 100

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    params = (
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
        mrglv1_pool_initialized_with_liquidity.maintenance(),
        mrglv1_pool_initialized_with_liquidity.oracle(),
        sender.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    mrglv1_initializer.initializePoolSqrtPriceX96(params, sender=sender)
    return mrglv1_pool_initialized_with_liquidity


@pytest.mark.integration
def test_arbitrageur_execute_with_univ3__sweeps_eth_with_marginal_price_higher(
    mrglv1_arbitrageur,
    mrglv1_pool_initialized_with_liquidity_price_higher,
    mrglv1_token0,
    mrglv1_token1,
    univ3_pool,
    WETH9,
    sender,
    alice,
    chain,
):
    state = mrglv1_pool_initialized_with_liquidity_price_higher.state()
    slot0 = univ3_pool.slot0()
    assert state.sqrtPriceX96 > slot0.sqrtPriceX96

    balance0_alice = mrglv1_token0.balanceOf(alice.address)
    balance1_alice = mrglv1_token1.balanceOf(alice.address)
    balancee_alice = alice.balance
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price > Uniswap price, so should take route for ETH out:
    # 1 => Uniswap => 0 => Marginal => 1
    assert univ3_pool.token1() == WETH9.address
    token_out = WETH9.address
    amount_out_min = 0
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    deadline = chain.pending_timestamp + 3600
    sweep_as_eth = True

    params = (
        mrglv1_pool_initialized_with_liquidity_price_higher.token0(),
        mrglv1_pool_initialized_with_liquidity_price_higher.token1(),
        mrglv1_pool_initialized_with_liquidity_price_higher.maintenance(),
        mrglv1_pool_initialized_with_liquidity_price_higher.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    mrglv1_arbitrageur.execute(params, sender=sender)

    state_after = mrglv1_pool_initialized_with_liquidity_price_higher.state()
    slot0_after = univ3_pool.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = mrglv1_token0.balanceOf(alice.address)
    balance1_alice_after = mrglv1_token1.balanceOf(alice.address)
    balancee_alice_after = alice.balance

    assert balance0_alice_after == 0
    assert balance1_alice_after == 0
    assert balancee_alice_after > balancee_alice


@pytest.mark.integration
def test_arbitrageur_execute_with_univ3__sweeps_eth_with_marginal_price_lower(
    mrglv1_arbitrageur,
    mrglv1_pool_initialized_with_liquidity_price_lower,
    mrglv1_token0,
    mrglv1_token1,
    univ3_pool,
    WETH9,
    sender,
    alice,
    chain,
):
    state = mrglv1_pool_initialized_with_liquidity_price_lower.state()
    slot0 = univ3_pool.slot0()
    assert state.sqrtPriceX96 < slot0.sqrtPriceX96

    balance0_alice = mrglv1_token0.balanceOf(alice.address)
    balance1_alice = mrglv1_token1.balanceOf(alice.address)
    balancee_alice = alice.balance
    assert balance0_alice == 0
    assert balance1_alice == 0

    # Marginal price < Uniswap price, so should take route for ETH out:
    # 1 => Marginal => 0 => Uniswap => 1
    assert univ3_pool.token1() == WETH9.address
    token_out = WETH9.address
    amount_out_min = 0
    sqrt_price_limit0_x96 = 0
    sqrt_price_limit1_x96 = 0
    deadline = chain.pending_timestamp + 3600
    sweep_as_eth = True

    params = (
        mrglv1_pool_initialized_with_liquidity_price_lower.token0(),
        mrglv1_pool_initialized_with_liquidity_price_lower.token1(),
        mrglv1_pool_initialized_with_liquidity_price_lower.maintenance(),
        mrglv1_pool_initialized_with_liquidity_price_lower.oracle(),
        alice.address,
        token_out,
        amount_out_min,
        sqrt_price_limit0_x96,
        sqrt_price_limit1_x96,
        deadline,
        sweep_as_eth,
    )
    mrglv1_arbitrageur.execute(params, sender=sender)

    state_after = mrglv1_pool_initialized_with_liquidity_price_lower.state()
    slot0_after = univ3_pool.slot0()
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-4) == slot0_after.sqrtPriceX96

    balance0_alice_after = mrglv1_token0.balanceOf(alice.address)
    balance1_alice_after = mrglv1_token1.balanceOf(alice.address)
    balancee_alice_after = alice.balance

    assert balance0_alice_after == 0
    assert balance1_alice_after == 0
    assert balancee_alice_after > balancee_alice
