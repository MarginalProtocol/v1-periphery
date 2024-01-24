import pytest

from ape.utils import ZERO_ADDRESS

from utils.constants import MINIMUM_LIQUIDITY, SECONDS_AGO, FEE, FEE_UNIT
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_sqrt_price_x96_from_tick,
)


def test_initializer_create_and_initialize_pool_if_necessary__creates_pool(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    initializer.createAndInitializePoolIfNecessary(params, sender=sender)

    # check pool created
    pool_address = factory.getPool(
        token0.address, token1.address, maintenance, mock_univ3_pool.address
    )
    assert pool_address != ZERO_ADDRESS
    assert factory.isPool(pool_address) is True


def test_initializer_create_and_initialize_pool_if_necessary__burns_liquidity(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    tx = initializer.createAndInitializePoolIfNecessary(params, sender=sender)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    pool_address = event.pool
    pool = project.MarginalV1Pool.at(pool_address)
    assert pool.balanceOf(pool.address) == liquidity_burned


def test_initializer_create_and_initialize_pool_if_necessary__initializes_pool_sqrt_price_x96(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    tx = initializer.createAndInitializePoolIfNecessary(params, sender=sender)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    pool_address = event.pool
    pool = project.MarginalV1Pool.at(pool_address)
    state = pool.state()
    assert pytest.approx(state.sqrtPriceX96, rel=1e-4) == slot0.sqrtPriceX96


def test_initializer_create_and_initialize_pool_if_necessary__mints_liquidity_for_amounts(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    tx = initializer.createAndInitializePoolIfNecessary(params, sender=sender)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    pool_address = event.pool
    pool = project.MarginalV1Pool.at(pool_address)
    state = pool.state()

    shares_alice = pool.balanceOf(alice.address)
    liquidity_alice = (shares_alice * state.liquidity) // pool.totalSupply()
    assert pytest.approx(liquidity_alice, rel=1e-10) == liquidity_desired


def test_initializer_create_and_initialize_pool_if_necessary__transfers_funds(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([SECONDS_AGO, 0])
    oracle_tick_avg = (
        oracle_tick_cumulatives[1] - oracle_tick_cumulatives[0]
    ) // SECONDS_AGO
    oracle_sqrt_price_x96 = calc_sqrt_price_x96_from_tick(oracle_tick_avg)

    (
        amount0_burned_on_mint,
        amount1_burned_on_mint,
    ) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_burned, oracle_sqrt_price_x96
    )

    (amount0_burned_on_swap, amount1_burned_on_swap) = swap_math_lib.swapAmounts(
        liquidity_burned,
        oracle_sqrt_price_x96,
        slot0.sqrtPriceX96,  # initialized to uni sqrt price
    )

    # include fees
    # TODO: test when accounting for protocol fees
    if amount0_burned_on_swap > 0:
        amount0_burned_on_swap += (amount0_burned_on_swap * FEE) // FEE_UNIT
    elif amount1_burned_on_swap > 0:
        amount1_burned_on_swap += (amount1_burned_on_swap * FEE) // FEE_UNIT

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    tx = initializer.createAndInitializePoolIfNecessary(params, sender=sender)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    pool_address = event.pool
    pool = project.MarginalV1Pool.at(pool_address)
    state = pool.state()

    shares_alice = pool.balanceOf(alice.address)
    liquidity_alice = (shares_alice * state.liquidity) // pool.totalSupply()
    (amount0_alice, amount1_alice) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_alice, state.sqrtPriceX96
    )

    amount0_in = amount0_burned_on_mint + amount0_burned_on_swap + amount0_alice
    amount1_in = amount1_burned_on_mint + amount1_burned_on_swap + amount1_alice

    assert (
        pytest.approx(token0.balanceOf(sender.address), rel=1e-10)
        == balance0_sender - amount0_in
    )
    assert (
        pytest.approx(token1.balanceOf(sender.address), rel=1e-10)
        == balance1_sender - amount1_in
    )
    assert pytest.approx(token0.balanceOf(pool_address), rel=1e-10) == amount0_in
    assert pytest.approx(token1.balanceOf(pool_address), rel=1e-10) == amount1_in

    assert token0.balanceOf(pool_address) == balance0_sender - token0.balanceOf(
        sender.address
    )
    assert token1.balanceOf(pool_address) == balance1_sender - token1.balanceOf(
        sender.address
    )


def test_initializer_create_and_initialize_pool_if_necessary__emits_event(
    initializer,
    mock_univ3_pool,
    factory,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    slot0 = mock_univ3_pool.slot0()  # univ3 slot0
    univ3_fee = mock_univ3_pool.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity
    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, slot0.sqrtPriceX96
    )

    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([SECONDS_AGO, 0])
    oracle_tick_avg = (
        oracle_tick_cumulatives[1] - oracle_tick_cumulatives[0]
    ) // SECONDS_AGO
    oracle_sqrt_price_x96 = calc_sqrt_price_x96_from_tick(oracle_tick_avg)

    (
        amount0_burned_on_mint,
        amount1_burned_on_mint,
    ) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_burned, oracle_sqrt_price_x96
    )

    (amount0_burned_on_swap, amount1_burned_on_swap) = swap_math_lib.swapAmounts(
        liquidity_burned,
        oracle_sqrt_price_x96,
        slot0.sqrtPriceX96,  # initialized to uni sqrt price
    )

    # include fees
    # TODO: test when accounting for protocol fees
    if amount0_burned_on_swap > 0:
        amount0_burned_on_swap += (amount0_burned_on_swap * FEE) // FEE_UNIT
    elif amount1_burned_on_swap > 0:
        amount1_burned_on_swap += (amount1_burned_on_swap * FEE) // FEE_UNIT

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    params = (
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        slot0.sqrtPriceX96,  # initializes to uni price
        sqrt_price_limit_x96,
        liquidity_burned,
        2**255 - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    tx = initializer.createAndInitializePoolIfNecessary(params, sender=sender)
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

    shares_alice = pool.balanceOf(alice.address)
    amount0_in = token0.balanceOf(pool_address)
    amount1_in = token1.balanceOf(pool_address)

    events = tx.decode_logs(initializer.PoolInitialize)
    assert len(events) == 1
    event = events[0]

    assert event.sender == sender.address
    assert event.pool == pool_address
    assert event.shares == shares_alice
    assert event.amount0 == amount0_in
    assert event.amount1 == amount1_in


# TODO: test price limits
