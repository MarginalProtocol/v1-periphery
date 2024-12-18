import pytest

from math import sqrt


@pytest.fixture(scope="module")
def sender(accounts):
    return accounts[3]


@pytest.fixture(scope="module")
def spot_reserve0(pool, token_a, token_b):
    x = int(125.04e12)  # e.g. USDC reserves on spot
    y = int(71.70e21)  # e.g. WETH reserves on spot
    return x if pool.token0() == token_a.address else y


@pytest.fixture(scope="module")
def spot_reserve1(pool, token_a, token_b):
    x = int(125.04e12)  # e.g. USDC reserves on spot
    y = int(71.70e21)  # e.g. WETH reserves on spot
    return y if pool.token1() == token_b.address else x


@pytest.fixture(scope="module")
def spot_liquidity(spot_reserve0, spot_reserve1):
    return int(sqrt(spot_reserve0 * spot_reserve1))


@pytest.fixture(scope="module")
def sqrt_price_x96_initial(spot_reserve0, spot_reserve1):
    sqrt_price = int(sqrt(spot_reserve1 / spot_reserve0))
    return sqrt_price << 96


@pytest.fixture(scope="module")
def token0(pool, token_a, token_b, sender, callee, router, manager, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(router.address, 2**256 - 1, sender=sender)
    token0.approve(manager.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, callee, router, manager, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(router.address, 2**256 - 1, sender=sender)
    token1.approve(manager.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1


@pytest.fixture(scope="module")
def pool_initialized_with_liquidity(
    pool,
    callee,
    token0,
    token1,
    sender,
    spot_liquidity,
    router,
):
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(pool.address, sender.address, liquidity_delta, sender=sender)
    pool.approve(pool.address, 2**256 - 1, sender=sender)
    pool.approve(router.address, 2**256 - 1, sender=sender)
    return pool


@pytest.fixture(scope="module")
def oracle_sqrt_price_initial_x96(
    pool_initialized_with_liquidity, mock_univ3_pool, oracle_lib
):
    seconds_ago = pool_initialized_with_liquidity.secondsAgo()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([seconds_ago, 0])
    sqrt_price_x96 = oracle_lib.oracleSqrtPriceX96(
        oracle_lib.oracleTickCumulativeDelta(
            oracle_tick_cumulatives[0], oracle_tick_cumulatives[1]
        ),
        seconds_ago,
    )
    return sqrt_price_x96
