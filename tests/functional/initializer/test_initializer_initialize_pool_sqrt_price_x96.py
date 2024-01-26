import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_LIQUIDITY
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


def test_initializer_initialize_pool_sqrt_price_x96__sets_to_sqrt_price_x96_when_greater_than_oracle(
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

    assert slot0.sqrtPriceX96 < state.sqrtPriceX96
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
    assert pytest.approx(result.sqrtPriceX96, rel=2e-4) == slot0.sqrtPriceX96


def test_initializer_initialize_pool_sqrt_price_x96__sets_to_sqrt_price_x96_when_less_than_oracle(
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

    assert slot0.sqrtPriceX96 < state.sqrtPriceX96
    assert state.liquidity == MINIMUM_LIQUIDITY**2

    amount_in_max = 2**256 - 1
    amount_out_min = 0
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    deadline = chain.pending_timestamp + 3600

    # move price on marginal pool to below uni price for test of less than sqrt price
    sqrt_price_x96_next = (slot0.sqrtPriceX96**2) // state.sqrtPriceX96
    assert sqrt_price_x96_next < slot0.sqrtPriceX96
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    state = pool.state()
    assert pytest.approx(state.sqrtPriceX96, rel=2e-4) == sqrt_price_x96_next

    assert slot0.sqrtPriceX96 > state.sqrtPriceX96
    zero_for_one = slot0.sqrtPriceX96 < state.sqrtPriceX96
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
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
    assert pytest.approx(result.sqrtPriceX96, rel=2e-4) == slot0.sqrtPriceX96


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
    assert slot0.sqrtPriceX96 < state.sqrtPriceX96
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
    assert pytest.approx(result.sqrtPriceX96, rel=2e-4) == slot0.sqrtPriceX96


def test_initializer_initialize_pool_sqrt_price_x96__set_to_min_sqrt_ratio_swaps_back(
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
    sqrt_price_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()

    amount_in_max = 0
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )

    zero_for_one = True
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        -reserve0 + 1 if not zero_for_one else -reserve1 + 1,
    )

    # mint large amounts
    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )

    if amount0_delta > 0:
        token0.mint(sender.address, amount0_delta * 10, sender=sender)
    elif amount1_delta > 0:
        token1.mint(sender.address, amount1_delta * 10, sender=sender)

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    state = pool.state()
    assert pytest.approx(state.sqrtPriceX96, rel=2e-1) == sqrt_price_x96_next

    # mint again to do next swap
    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )

    # mint large amounts
    if amount0_delta > 0:
        token0.mint(sender.address, amount0_delta * 10, sender=sender)
    elif amount1_delta > 0:
        token1.mint(sender.address, amount1_delta * 10, sender=sender)

    # move price back to uni price
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
    assert pytest.approx(result.sqrtPriceX96, rel=1e-3) == slot0.sqrtPriceX96


def test_initializer_initialize_pool_sqrt_price_x96__set_to_max_sqrt_ratio_swaps_back(
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
    sqrt_price_math_lib,
):
    # add minimum amount of liquidity
    callee.mint(pool.address, sender.address, MINIMUM_LIQUIDITY**2, sender=sender)

    slot0 = mock_univ3_pool.slot0()
    state = pool.state()

    amount_in_max = 0
    amount_out_min = 0
    sqrt_price_limit_x96 = 0
    deadline = chain.pending_timestamp + 3600

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )

    zero_for_one = False
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        -reserve0 + 1 if not zero_for_one else -reserve1 + 1,
    )

    # mint large amounts
    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )

    if amount0_delta > 0:
        token0.mint(sender.address, amount0_delta * 10, sender=sender)
    elif amount1_delta > 0:
        token1.mint(sender.address, amount1_delta * 10, sender=sender)

    # move price on marginal pool to uni price
    params = (
        pool.token0(),
        pool.token1(),
        pool.maintenance(),
        pool.oracle(),
        alice.address,
        sqrt_price_x96_next,
        amount_in_max,
        amount_out_min,
        sqrt_price_limit_x96,
        deadline,
    )
    initializer.initializePoolSqrtPriceX96(params, sender=sender)

    state = pool.state()
    assert pytest.approx(state.sqrtPriceX96, rel=2e-1) == sqrt_price_x96_next

    # mint again to do next swap
    (amount0_delta, amount1_delta) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )

    # mint large amounts
    if amount0_delta > 0:
        token0.mint(sender.address, amount0_delta * 10, sender=sender)
    elif amount1_delta > 0:
        token1.mint(sender.address, amount1_delta * 10, sender=sender)

    # move price back to uni price
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
    assert pytest.approx(result.sqrtPriceX96, rel=1e-3) == slot0.sqrtPriceX96


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
    assert slot0.sqrtPriceX96 < state.sqrtPriceX96
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
