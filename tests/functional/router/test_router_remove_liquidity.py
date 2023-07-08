def test_remove_liquidity__updates_liquidity(
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


def test_remove_liquidity__burns_shares():
    pass


def test_remove_liquidity__transfers_funds():
    pass


def test_remove_liquidity__emits_decrease_liquidity():
    pass


# TODO:
def test_remove_liquidity__deposits_weth():
    pass


def test_remove_liquidity__reverts_when_past_deadline():
    pass


def test_remove_liquidity__reverts_when_amount0_less_than_min():
    pass


def test_remove_liquidity__reverts_when_amount1_less_than_min():
    pass
