from ape import reverts


def test_router_remove_liquidity__updates_liquidity(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    shares = shares_sender // 2
    liquidity_delta = (total_liquidity * shares) // total_shares
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )
    router.removeLiquidity(params, sender=sender)

    assert (
        pool_initialized_with_liquidity.state().liquidity
        == state.liquidity - liquidity_delta
    )


def test_router_remove_liquidity__burns_shares(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
):
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    shares = shares_sender // 2
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )
    router.removeLiquidity(params, sender=sender)

    assert (
        pool_initialized_with_liquidity.balanceOf(sender.address)
        == shares_sender - shares
    )
    assert pool_initialized_with_liquidity.totalSupply() == total_shares - shares


def test_router_remove_liquidity__transfers_funds(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    token0,
    token1,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    shares = shares_sender // 2
    liquidity_delta = (total_liquidity * shares) // total_shares
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )
    router.removeLiquidity(params, sender=sender)

    assert token0.balanceOf(alice.address) == balance0_alice + amount0
    assert token1.balanceOf(alice.address) == balance1_alice + amount1

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool - amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool - amount1
    )


def test_router_remove_liquidity__emits_decrease_liquidity(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    shares = shares_sender // 2
    liquidity_delta = (total_liquidity * shares) // total_shares
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )
    tx = router.removeLiquidity(params, sender=sender)

    events = tx.decode_logs(router.DecreaseLiquidity)
    assert len(events) == 1

    event = events[0]
    assert event.shares == shares
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1


# TODO:
def test_router_remove_liquidity__deposits_weth():
    pass


def test_router_remove_liquidity__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
):
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    shares = shares_sender // 2
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp - 1
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )

    with reverts("Transaction too old"):
        router.removeLiquidity(params, sender=sender)


def test_router_remove_liquidity__reverts_when_amount0_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    shares = shares_sender // 2
    liquidity_delta = (total_liquidity * shares) // total_shares
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)

    amount0_min = amount0 + 1
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )

    with reverts(router.Amount0LessThanMin, amount0=amount0):
        router.removeLiquidity(params, sender=sender)


def test_router_remove_liquidity__reverts_when_amount1_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity + pool_initialized_with_liquidity.liquidityLocked()
    )

    shares = shares_sender // 2
    liquidity_delta = (total_liquidity * shares) // total_shares
    amount0, amount1 = liquidity_math_lib.toAmounts(liquidity_delta, state.sqrtPriceX96)

    amount0_min = 0
    amount1_min = amount1 + 1
    deadline = chain.pending_timestamp + 3600
    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )

    with reverts(router.Amount1LessThanMin, amount1=amount1):
        router.removeLiquidity(params, sender=sender)
