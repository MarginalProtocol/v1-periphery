import pytest

from ape import reverts
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


@pytest.mark.parametrize("rel_sqrt_price_from_oracle", [0.99, 1.01])
def test_initializer_create_and_initialize_pool_if_necessary__deposits_WETH9(
    initializer,
    mock_univ3_pool_with_WETH9,
    factory,
    callee,
    sender,
    alice,
    token0_with_WETH9,
    token1_with_WETH9,
    WETH9,
    chain,
    swap_math_lib,
    spot_liquidity,
    project,
    rel_sqrt_price_from_oracle,
):
    maintenance = 1000000  # pool three
    sqrt_price_limit_x96 = 0  # either extreme of range as limit
    liquidity_burned = MINIMUM_LIQUIDITY**2
    deadline = chain.pending_timestamp + 3600

    # set WETH9 allowance to zero to ensure all payment in ETH
    WETH9.approve(initializer.address, 0, sender=sender)

    univ3_fee = mock_univ3_pool_with_WETH9.fee()
    liquidity_desired = (spot_liquidity * 10) // 10000  # 0.1% of spot liquidity

    oracle_tick_cumulatives, _ = mock_univ3_pool_with_WETH9.observe([SECONDS_AGO, 0])
    oracle_tick_avg = (
        oracle_tick_cumulatives[1] - oracle_tick_cumulatives[0]
    ) // SECONDS_AGO
    oracle_sqrt_price_x96 = calc_sqrt_price_x96_from_tick(oracle_tick_avg)
    sqrt_price_x96 = int(rel_sqrt_price_from_oracle * oracle_sqrt_price_x96)

    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_desired, sqrt_price_x96
    )

    # cache balances prior
    balance0_sender = token0_with_WETH9.balanceOf(sender.address)
    balance1_sender = token1_with_WETH9.balanceOf(sender.address)
    balancee_sender = sender.balance
    balancee_WETH9 = WETH9.balance

    (
        amount0_burned_on_mint,
        amount1_burned_on_mint,
    ) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_burned, oracle_sqrt_price_x96
    )

    (amount0_burned_on_swap, amount1_burned_on_swap) = swap_math_lib.swapAmounts(
        liquidity_burned,
        oracle_sqrt_price_x96,
        sqrt_price_x96,  # initialized to sqrt price
    )

    # include fees
    # TODO: test when accounting for protocol fees
    if amount0_burned_on_swap > 0:
        amount0_burned_on_swap += (amount0_burned_on_swap * FEE) // FEE_UNIT
    elif amount1_burned_on_swap > 0:
        amount1_burned_on_swap += (amount1_burned_on_swap * FEE) // FEE_UNIT

    # totals for amounts burned
    amount0_burned = amount0_burned_on_mint + amount0_burned_on_swap
    amount1_burned = amount1_burned_on_mint + amount1_burned_on_swap

    # check not already created marginal pool
    assert (
        factory.getPool(
            token0_with_WETH9.address,
            token1_with_WETH9.address,
            maintenance,
            mock_univ3_pool_with_WETH9.address,
        )
        == ZERO_ADDRESS
    )

    params = (
        token0_with_WETH9.address,
        token1_with_WETH9.address,
        maintenance,
        univ3_fee,
        alice.address,  # recipient of the LP token minted
        sqrt_price_x96,  # initializes to sqrt price
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
    amounte_desired = (
        amount1_desired + amount1_burned
        if token1_with_WETH9.address == WETH9.address
        else amount0_desired + amount0_burned
    )
    value = (
        amounte_desired * 101
    ) // 100  # send escess ETH to test initializer refunds

    tx = initializer.createAndInitializePoolIfNecessary(
        params, sender=sender, value=value
    )
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

    amount0_in_sender = (
        amount0_burned + amount0_alice
        if token0_with_WETH9.address != WETH9.address
        else 0
    )
    amount1_in_sender = (
        amount1_burned + amount1_alice
        if token1_with_WETH9.address != WETH9.address
        else 0
    )
    amounte_in_sender = (
        amount0_burned + amount0_alice
        if token0_with_WETH9.address == WETH9.address
        else amount1_burned + amount1_alice
    )

    amount0_to_pool = amount0_burned + amount0_alice
    amount1_to_pool = amount1_burned + amount1_alice

    assert (
        pytest.approx(token0_with_WETH9.balanceOf(sender.address), rel=1e-9)
        == balance0_sender - amount0_in_sender
    )
    assert (
        pytest.approx(token1_with_WETH9.balanceOf(sender.address), rel=1e-9)
        == balance1_sender - amount1_in_sender
    )

    assert initializer.balance == 0  # refunded ETH
    assert (
        pytest.approx(sender.balance, rel=1e-10)
        == balancee_sender - amounte_in_sender - tx.gas_used * tx.gas_price
    )  # check refunds excess

    assert (
        pytest.approx(token0_with_WETH9.balanceOf(pool_address), rel=1e-9)
        == amount0_to_pool
    )
    assert (
        pytest.approx(token1_with_WETH9.balanceOf(pool_address), rel=1e-9)
        == amount1_to_pool
    )
    assert pytest.approx(WETH9.balance, rel=1e-9) == balancee_WETH9 + amounte_in_sender

    balance0_sender_diff = balance0_sender - token0_with_WETH9.balanceOf(sender.address)
    balance1_sender_diff = balance1_sender - token1_with_WETH9.balanceOf(sender.address)
    balancee_sender_diff = balancee_sender - (
        sender.balance + tx.gas_used * tx.gas_price
    )

    assert pytest.approx(token0_with_WETH9.balanceOf(pool_address), rel=1e-9) == (
        balance0_sender_diff
        if token0_with_WETH9.address != WETH9.address
        else balancee_sender_diff
    )
    assert pytest.approx(token1_with_WETH9.balanceOf(pool_address), rel=1e-9) == (
        balance1_sender_diff
        if token1_with_WETH9.address != WETH9.address
        else balancee_sender_diff
    )


def test_initializer_create_and_initialize_pool_if_necessary__reverts_when_oracle_invalid(
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
        univ3_fee + 1,  # should yield invalid oracle since not a fee tier
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
    with reverts(initializer.InvalidOracle):
        initializer.createAndInitializePoolIfNecessary(params, sender=sender)


def test_initializer_create_and_initialize_pool_if_necessary__reverts_when_liquidity_burned_less_than_min(
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
    liquidity_burned = MINIMUM_LIQUIDITY
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

    with reverts(initializer.LiquidityBurnedLessThanMin):
        initializer.createAndInitializePoolIfNecessary(params, sender=sender)


def test_initializer_create_and_initialize_pool_if_necessary__reverts_when_amount0_burned_greater_than_max(
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

    amount0_burned = amount0_burned_on_mint + amount0_burned_on_swap

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
        amount0_burned - 1,  # amount0 burned max
        2**255 - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    # @dev off by 1 in unit test due to rounding diff in contracts
    with reverts(
        initializer.Amount0BurnedGreaterThanMax, amount0Burned=amount0_burned + 1
    ):
        initializer.createAndInitializePoolIfNecessary(params, sender=sender)


def test_initializer_create_and_initialize_pool_if_necessary__reverts_when_amount1_burned_greater_than_max(
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

    amount1_burned = amount1_burned_on_mint + amount1_burned_on_swap

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
        amount1_burned - 1,  # amount1 burned max
        amount0_desired,  # amount0 desired in LP
        amount1_desired,  # amount1 desired in LP
        0,  # amount0 min in LP
        0,  # amount1 min in LP
        deadline,
    )

    # @dev off by rel ~1e-5 in unit test due to rounding diff in contracts
    with reverts(initializer.Amount1BurnedGreaterThanMax):
        initializer.createAndInitializePoolIfNecessary(params, sender=sender)
