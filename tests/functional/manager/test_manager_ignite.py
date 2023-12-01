import pytest

from ape import reverts
from ape.utils import ZERO_ADDRESS

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def spot_pool_initialized_with_liquidity(
    mock_univ3_pool,
    spot_liquidity,
    sqrt_price_x96_initial,
    token0,
    token1,
    sender,
):
    slot0 = mock_univ3_pool.slot0()
    slot0.sqrtPriceX96 = (
        sqrt_price_x96_initial  # have prices coincide between spot and marginal
    )
    mock_univ3_pool.setSlot0(slot0, sender=sender)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        spot_liquidity, slot0.sqrtPriceX96
    )
    token0.mint(mock_univ3_pool.address, reserve0, sender=sender)
    token1.mint(mock_univ3_pool.address, reserve1, sender=sender)
    mock_univ3_pool.setLiquidity(spot_liquidity, sender=sender)

    return mock_univ3_pool


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    chain,
    manager,
    sender,
):
    def mint(zero_for_one: bool) -> int:
        state = pool_initialized_with_liquidity.state()
        maintenance = pool_initialized_with_liquidity.maintenance()
        oracle = pool_initialized_with_liquidity.oracle()

        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )
        (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
            state.liquidity, state.sqrtPriceX96
        )
        reserve = reserve1 if zero_for_one else reserve0

        size = reserve * 1 // 100  # 1% of reserves
        margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
        size_min = (size * 80) // 100
        debt_max = 2**128 - 1
        amount_in_max = 2**256 - 1
        deadline = chain.pending_timestamp + 3600

        mint_params = (
            pool_initialized_with_liquidity.token0(),
            pool_initialized_with_liquidity.token1(),
            maintenance,
            oracle,
            zero_for_one,
            size,
            size_min,
            debt_max,
            amount_in_max,
            sqrt_price_limit_x96,
            margin,
            sender.address,
            deadline,
        )
        tx = manager.mint(mint_params, sender=sender)
        token_id = tx.decode_logs(manager.Mint)[0].tokenId
        return int(token_id)

    yield mint


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__settles_position(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    block_timestamp_next = chain.pending_timestamp
    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    manager.ignite(ignite_params, sender=sender)

    state = pool_initialized_with_liquidity.state()
    tick_cumulative_last = state.tickCumulative
    oracle_tick_cumulatives, _ = spot_pool_initialized_with_liquidity.observe([0])

    # sync then settle position
    position = position_lib.sync(
        position,
        block_timestamp_next,
        tick_cumulative_last,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    position = position_lib.settle(position)
    assert pool_initialized_with_liquidity.positions(key) == position


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__transfers_funds(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    token0,
    token1,
    position_lib,
    swap_math_lib,
    sqrt_price_math_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    reward = pool_initialized_with_liquidity.reward()
    position_id = pool_initialized_with_liquidity.state().totalPositions - 1

    spot_slot0 = spot_pool_initialized_with_liquidity.slot0()
    spot_liquidity = spot_pool_initialized_with_liquidity.liquidity()
    spot_fee = spot_pool_initialized_with_liquidity.fee()

    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position_lib.liquidationRewards(position.size, reward)

    token_in = token0 if zero_for_one else token1
    token_out = token1 if zero_for_one else token0

    amount_in = (
        position.debt0 if zero_for_one else position.debt1
    )  # out from spot pool to repay
    amount_out = position.size + position.margin + rewards

    # calculate amount out from spot pool to subtract from amount_out
    amount_specified = -amount_in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        (not zero_for_one),  # if debt in is 0 to marginal, need 0 out from spot
        amount_specified,
    )

    (spot_amount0, spot_amount1) = swap_math_lib.swapAmounts(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    if zero_for_one:
        # zero debt into marginal means zero taken out of spot pool to repay (1 into spot)
        spot_amount1 += swap_math_lib.swapFees(spot_amount1, spot_fee)
    else:
        # one debt into marginal means one taken out of spot pool to repay (0 into spot)
        spot_amount0 += swap_math_lib.swapFees(spot_amount0, spot_fee)

    spot_amount_in = spot_amount1 if zero_for_one else spot_amount0

    # adjust amount out based off spot swap amount in required to repay debt
    amount_out_recipient = amount_out - spot_amount_in

    # cache balances before ignite
    balance_out_alice = token_out.balanceOf(alice.address)
    balance_out_pool = token_out.balanceOf(pool_initialized_with_liquidity.address)
    balance_out_spot_pool = token_out.balanceOf(
        spot_pool_initialized_with_liquidity.address
    )

    balance_in_pool = token_in.balanceOf(pool_initialized_with_liquidity.address)
    balance_in_spot_pool = token_in.balanceOf(
        spot_pool_initialized_with_liquidity.address
    )

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    manager.ignite(ignite_params, sender=sender)

    assert (
        token_out.balanceOf(alice.address) == balance_out_alice + amount_out_recipient
    )
    assert (
        token_out.balanceOf(pool_initialized_with_liquidity.address)
        == balance_out_pool - amount_out
    )
    assert (
        token_in.balanceOf(pool_initialized_with_liquidity.address)
        == balance_in_pool + amount_in
    )
    assert (
        token_out.balanceOf(spot_pool_initialized_with_liquidity.address)
        == balance_out_spot_pool + spot_amount_in
    )
    assert (
        token_in.balanceOf(spot_pool_initialized_with_liquidity.address)
        == balance_in_spot_pool - amount_in
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__deletes_manager_position(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    manager_position = manager.positions(token_id)
    assert manager_position.pool != ZERO_ADDRESS

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    manager.ignite(ignite_params, sender=sender)

    # view should revert since Position struct has ZERO_ADDRESS for pool
    with reverts():
        manager.positions(token_id)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__burns_token(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    assert manager.ownerOf(token_id) == sender.address
    assert manager.balanceOf(sender.address) > 0

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    manager.ignite(ignite_params, sender=sender)

    assert manager.balanceOf(sender.address) == 0


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__emits_ignite(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    swap_math_lib,
    sqrt_price_math_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    reward = pool_initialized_with_liquidity.reward()
    position_id = pool_initialized_with_liquidity.state().totalPositions - 1

    spot_slot0 = spot_pool_initialized_with_liquidity.slot0()
    spot_liquidity = spot_pool_initialized_with_liquidity.liquidity()
    spot_fee = spot_pool_initialized_with_liquidity.fee()

    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position_lib.liquidationRewards(position.size, reward)

    amount_in = (
        position.debt0 if zero_for_one else position.debt1
    )  # out from spot pool to repay
    amount_out = position.size + position.margin + rewards

    # calculate amount out from spot pool to subtract from amount_out
    amount_specified = -amount_in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        (not zero_for_one),  # if debt in is 0 to marginal, need 0 out from spot
        amount_specified,
    )

    (spot_amount0, spot_amount1) = swap_math_lib.swapAmounts(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    if zero_for_one:
        # zero debt into marginal means zero taken out of spot pool to repay (1 into spot)
        spot_amount1 += swap_math_lib.swapFees(spot_amount1, spot_fee)
    else:
        # one debt into marginal means one taken out of spot pool to repay (0 into spot)
        spot_amount0 += swap_math_lib.swapFees(spot_amount0, spot_fee)

    spot_amount_in = spot_amount1 if zero_for_one else spot_amount0

    # adjust amount out based off spot swap amount in required to repay debt
    amount_out_recipient = amount_out - spot_amount_in

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    tx = manager.ignite(ignite_params, sender=sender)
    events = tx.decode_logs(manager.Ignite)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == token_id
    assert event.amountOut == amount_out_recipient
    # assert tx.return_value == amount_out_recipient  # TODO: fix


# TODO:
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__deposits_weth(zero_for_one):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__reverts_when_not_owner(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    amount_out_min = 0
    deadline = chain.pending_timestamp + 3600
    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    with reverts(manager.Unauthorized):
        manager.ignite(ignite_params, sender=alice)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    amount_out_min = 0
    deadline = chain.pending_timestamp - 1
    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    with reverts("Transaction too old"):
        manager.ignite(ignite_params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__reverts_when_invalid_pool_key(
    rando_pool,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    amount_out_min = 0
    deadline = chain.pending_timestamp + 3600
    ignite_params = (
        rando_pool.token0(),
        rando_pool.token1(),
        rando_pool.maintenance(),
        rando_pool.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    with reverts(manager.InvalidPoolKey):
        manager.ignite(ignite_params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite__reverts_when_amount_less_than_min(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    swap_math_lib,
    sqrt_price_math_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    reward = pool_initialized_with_liquidity.reward()
    position_id = pool_initialized_with_liquidity.state().totalPositions - 1

    spot_slot0 = spot_pool_initialized_with_liquidity.slot0()
    spot_liquidity = spot_pool_initialized_with_liquidity.liquidity()
    spot_fee = spot_pool_initialized_with_liquidity.fee()

    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position_lib.liquidationRewards(position.size, reward)

    amount_in = (
        position.debt0 if zero_for_one else position.debt1
    )  # out from spot pool to repay
    amount_out = position.size + position.margin + rewards

    # calculate amount out from spot pool to subtract from amount_out
    amount_specified = -amount_in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        (not zero_for_one),  # if debt in is 0 to marginal, need 0 out from spot
        amount_specified,
    )

    (spot_amount0, spot_amount1) = swap_math_lib.swapAmounts(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    if zero_for_one:
        # zero debt into marginal means zero taken out of spot pool to repay (1 into spot)
        spot_amount1 += swap_math_lib.swapFees(spot_amount1, spot_fee)
    else:
        # one debt into marginal means one taken out of spot pool to repay (0 into spot)
        spot_amount0 += swap_math_lib.swapFees(spot_amount0, spot_fee)

    spot_amount_in = spot_amount1 if zero_for_one else spot_amount0

    # adjust amount out based off spot swap amount in required to repay debt
    amount_out_recipient = amount_out - spot_amount_in

    deadline = chain.pending_timestamp + 3600
    amount_out_min = amount_out_recipient + 1

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    with reverts(manager.AmountOutLessThanMin, amountOut=amount_out_recipient):
        manager.ignite(ignite_params, sender=sender)
