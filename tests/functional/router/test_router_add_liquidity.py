from ape import reverts


def test_router_add_liquidity__updates_liquidity(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
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
    router.addLiquidity(params, sender=sender)

    assert (
        pool_initialized_with_liquidity.state().liquidity
        == state.liquidity + liquidity_delta
    )


def test_router_add_liquidity__mints_shares(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_before = pool_initialized_with_liquidity.balanceOf(alice.address)
    total_shares_before = pool_initialized_with_liquidity.totalSupply()
    total_liquidity_before = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )

    shares = (liquidity_delta * total_shares_before) // total_liquidity_before
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
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
    router.addLiquidity(params, sender=sender)

    assert (
        pool_initialized_with_liquidity.balanceOf(alice.address)
        == shares_before + shares
    )
    assert pool_initialized_with_liquidity.totalSupply() == total_shares_before + shares


def test_router_add_liquidity__transfers_funds(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    token0,
    token1,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)
    amount0 += 1  # @dev rough round up
    amount1 += 1

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
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
    router.addLiquidity(params, sender=sender)

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )


def test_router_add_liquidity__emits_increase_liquidity(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    total_shares_before = pool_initialized_with_liquidity.totalSupply()
    total_liquidity_before = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)
    amount0 += 1  # @dev rough round up
    amount1 += 1

    shares = (liquidity_delta * total_shares_before) // total_liquidity_before

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
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
    tx = router.addLiquidity(params, sender=sender)
    events = tx.decode_logs(router.IncreaseLiquidity)
    assert len(events) == 1

    event = events[0]
    assert event.shares == shares
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1


def test_router_add_liquidity__deposits_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_with_WETH9_initialized_with_liquidity.state()

    # set WETH9 allowance to zero to ensure all payment in ETH
    WETH9.approve(router.address, 0, sender=sender)

    balance0_sender = token0_with_WETH9.balanceOf(sender.address)
    balance1_sender = token1_with_WETH9.balanceOf(sender.address)
    balancee_sender = sender.balance

    balance0_pool = token0_with_WETH9.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )
    balance1_pool = token1_with_WETH9.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )

    balancee_WETH9 = WETH9.balance

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)
    amount0 += 1  # @dev rough round up
    amount1 += 1

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_with_WETH9_initialized_with_liquidity.token0(),
        pool_with_WETH9_initialized_with_liquidity.token1(),
        pool_with_WETH9_initialized_with_liquidity.maintenance(),
        pool_with_WETH9_initialized_with_liquidity.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )
    value = amount0 if token0_with_WETH9.address == WETH9.address else amount1
    value = (value * 101) // 100  # add some excess in case pool price moves
    tx = router.addLiquidity(params, sender=sender, value=value)

    amount0_sender = amount0 if token0_with_WETH9.address != WETH9.address else 0
    amount1_sender = amount1 if token1_with_WETH9.address != WETH9.address else 0
    amounte_sender = (
        amount0 if token0_with_WETH9.address == WETH9.address else amount1
    )  # router handles refund of excess value

    assert (
        token0_with_WETH9.balanceOf(sender.address) == balance0_sender - amount0_sender
    )
    assert (
        token0_with_WETH9.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1_with_WETH9.balanceOf(sender.address) == balance1_sender - amount1_sender
    )
    assert (
        token1_with_WETH9.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )
    assert (
        sender.balance == balancee_sender - amounte_sender - tx.gas_used * tx.gas_price
    )  # router handles refund of excess value
    assert WETH9.balance == balancee_WETH9 + amounte_sender


def test_router_add_liquidity__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp - 1
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

    with reverts("Transaction too old"):
        router.addLiquidity(params, sender=sender)


def test_router_add_liquidity__reverts_when_pool_not_initialized(
    pool_two,
    router,
    sender,
    alice,
    chain,
    spot_reserve0,
    spot_reserve1,
):
    state = pool_two.state()
    assert state.initialized is False

    amount0_desired = spot_reserve0 * 1 // 100
    amount1_desired = spot_reserve1 * 1 // 100
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_two.token0(),
        pool_two.token1(),
        pool_two.maintenance(),
        pool_two.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )

    with reverts("Pool not initialized"):
        router.addLiquidity(params, sender=sender)


def test_router_add_liquidity__reverts_when_amount0_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)
    amount0 += 1  # @dev rough round up
    amount1 += 1

    amount0_min = amount0 + 1
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
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

    with reverts(router.Amount0LessThanMin, amount0=amount0):
        router.addLiquidity(params, sender=sender)


def test_router_add_liquidity__reverts_when_amount1_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
    liquidity_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state.sqrtPriceX96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)
    amount0 += 1  # @dev rough round up
    amount1 += 1

    amount0_min = 0
    amount1_min = amount1 + 1
    deadline = chain.pending_timestamp + 3600
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

    with reverts(router.Amount1LessThanMin, amount1=amount1):
        router.addLiquidity(params, sender=sender)
