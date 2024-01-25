import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_LIQUIDITY


def test_initializer_initialize_pool_sqrt_price_x96__sets_to_sqrt_price_x96(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )

    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    result = pool.state()
    assert pytest.approx(result.sqrtPriceX96, rel=1e-4) == slot0.sqrtPriceX96


def test_initializer_initialize_pool_sqrt_price_x96__sets_to_sqrt_price_x96_when_amount_in_max_zero(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 0
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )

    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    result = pool.state()
    assert pytest.approx(result.sqrtPriceX96, rel=1e-4) == slot0.sqrtPriceX96


def test_initializer_initialize_pool_sqrt_price_x96__reverts_when_token0_greater_than_token1(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    # move price on marginal pool to uni price
    params = (
        pool.token1(),
        pool.token0(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    with reverts():
        initializer.initializePoolSqrtPriceX96(params, sender=sender)


def test_initializer_initialize_pool_sqrt_price_x96__reverts_when_pool_not_initialized(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert state.initialized is False

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    with reverts(initializer.PoolNotInitialized):
        initializer.initializePoolSqrtPriceX96(params, sender=sender)


def test_initializer_initialize_pool_sqrt_price_x96__reverts_when_amount_in_greater_than_max(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )
    amount_in_max = amount0_delta // 2 if amount0_delta > 0 else amount1_delta // 2

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    with reverts(initializer.AmountInGreaterThanMax):
        initializer.initializePoolSqrtPriceX96(params, sender=sender)


def test_initializer_initialize_pool_sqrt_price_x96__reverts_when_amount_out_less_than_min(
    initializer,
    mock_univ3_pool,
    pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()
    assert slot0.sqrtPriceX96 != state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 2**256 - 1
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )
    amount_out_min = (
        int(-amount0_delta * 2) if amount0_delta < 0 else int(-amount1_delta * 2)
    )

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        slot0.sqrtPriceX96,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    with reverts(initializer.AmountOutLessThanMin):
        initializer.initializePoolSqrtPriceX96(params, sender=sender)
