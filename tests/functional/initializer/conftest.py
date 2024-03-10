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
def token0(pool, token_a, token_b, sender, callee, initializer, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(initializer.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, callee, initializer, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(initializer.address, 2**256 - 1, sender=sender)
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
    initializer,
):
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(pool.address, sender.address, liquidity_delta, sender=sender)
    pool.approve(pool.address, 2**256 - 1, sender=sender)
    pool.approve(initializer.address, 2**256 - 1, sender=sender)
    return pool


@pytest.fixture(scope="module")
def token0_with_WETH9(
    pool_with_WETH9, token_a, WETH9, sender, callee, initializer, spot_reserve0, chain
):
    _token0 = token_a if pool_with_WETH9.token0() == token_a.address else WETH9
    _token0.approve(callee.address, 2**256 - 1, sender=sender)
    _token0.approve(initializer.address, 2**256 - 1, sender=sender)

    if _token0.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve0 + sender.balance)
        WETH9.deposit(value=spot_reserve0, sender=sender)
    else:
        _token0.mint(sender.address, spot_reserve0, sender=sender)
    return _token0


@pytest.fixture(scope="module")
def token1_with_WETH9(
    pool_with_WETH9, token_a, WETH9, sender, callee, initializer, spot_reserve1, chain
):
    _token1 = WETH9 if pool_with_WETH9.token1() == WETH9.address else token_a
    _token1.approve(callee.address, 2**256 - 1, sender=sender)
    _token1.approve(initializer.address, 2**256 - 1, sender=sender)

    if _token1.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve1 + sender.balance)
        WETH9.deposit(value=spot_reserve1, sender=sender)
    else:
        _token1.mint(sender.address, spot_reserve1, sender=sender)
    return _token1


@pytest.fixture(scope="module")
def pool_with_WETH9_initialized_with_liquidity(
    pool_with_WETH9,
    callee,
    token0_with_WETH9,
    token1_with_WETH9,
    sender,
    spot_liquidity,
    initializer,
):
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(pool_with_WETH9.address, sender.address, liquidity_delta, sender=sender)
    pool_with_WETH9.approve(pool_with_WETH9.address, 2**256 - 1, sender=sender)
    pool_with_WETH9.approve(initializer.address, 2**256 - 1, sender=sender)
    return pool_with_WETH9
