import pytest

from ape import reverts
from ape.utils import ZERO_ADDRESS

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity, position_lib, chain, manager, sender
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

        premium = pool_initialized_with_liquidity.rewardPremium()
        base_fee = chain.blocks[-1].base_fee
        rewards = position_lib.liquidationRewards(
            base_fee,
            BASE_FEE_MIN,
            GAS_LIQUIDATE,
            premium,
        )

        tx = manager.mint(mint_params, sender=sender, value=rewards)
        token_id = tx.decode_logs(manager.Mint)[0].tokenId
        return int(token_id)

    yield mint


@pytest.fixture
def mint_position_with_WETH9(
    pool_with_WETH9_initialized_with_liquidity, chain, position_lib, manager, sender
):
    def mint(zero_for_one: bool) -> int:
        state = pool_with_WETH9_initialized_with_liquidity.state()
        maintenance = pool_with_WETH9_initialized_with_liquidity.maintenance()
        oracle = pool_with_WETH9_initialized_with_liquidity.oracle()

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
            pool_with_WETH9_initialized_with_liquidity.token0(),
            pool_with_WETH9_initialized_with_liquidity.token1(),
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

        premium = pool_with_WETH9_initialized_with_liquidity.rewardPremium()
        base_fee = chain.blocks[-1].base_fee
        rewards = position_lib.liquidationRewards(
            base_fee,
            BASE_FEE_MIN,
            GAS_LIQUIDATE,
            premium,
        )

        tx = manager.mint(mint_params, sender=sender, value=rewards)
        token_id = tx.decode_logs(manager.Mint)[0].tokenId
        return int(token_id)

    yield mint


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__settles_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mock_univ3_pool,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    block_timestamp_next = chain.pending_timestamp
    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    manager.burn(burn_params, sender=sender)

    state = pool_initialized_with_liquidity.state()
    tick_cumulative_last = state.tickCumulative
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])

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
def test_manager_burn__transfers_funds(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    token0,
    token1,
    position_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    rewards = position.rewards

    token_in = token0 if zero_for_one else token1
    token_out = token1 if zero_for_one else token0

    amount_in = position.debt0 if zero_for_one else position.debt1
    amount_out = position.size + position.margin

    balance_in_sender = token_in.balanceOf(sender.address)
    balance_in_pool = token_in.balanceOf(pool_initialized_with_liquidity.address)

    balance_out_alice = token_out.balanceOf(alice.address)
    balance_out_pool = token_out.balanceOf(pool_initialized_with_liquidity.address)

    balancee_alice = alice.balance
    balancee_pool = pool_initialized_with_liquidity.balance

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    manager.burn(burn_params, sender=sender)

    assert token_out.balanceOf(alice.address) == balance_out_alice + amount_out
    assert token_in.balanceOf(sender.address) == balance_in_sender - amount_in

    assert (
        token_out.balanceOf(pool_initialized_with_liquidity.address)
        == balance_out_pool - amount_out
    )
    assert (
        token_in.balanceOf(pool_initialized_with_liquidity.address)
        == balance_in_pool + amount_in
    )

    assert alice.balance == balancee_alice + rewards
    assert pool_initialized_with_liquidity.balance == balancee_pool - rewards


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__deletes_manager_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    manager_position = manager.positions(token_id)
    assert manager_position.pool != ZERO_ADDRESS

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    manager.burn(burn_params, sender=sender)

    # view should revert since Position struct has ZERO_ADDRESS for pool
    with reverts():
        manager.positions(token_id)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__burns_token(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    assert manager.ownerOf(token_id) == sender.address
    assert manager.balanceOf(sender.address) > 0

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    manager.burn(burn_params, sender=sender)

    assert manager.balanceOf(sender.address) == 0


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__emits_burn(
    pool_initialized_with_liquidity,
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

    rewards = position.rewards
    amount_in = position.debt0 if zero_for_one else position.debt1
    amount_out = position.size + position.margin

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    tx = manager.burn(burn_params, sender=sender)
    events = tx.decode_logs(manager.Burn)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == token_id
    assert event.sender == sender.address
    assert event.recipient == alice.address
    assert event.amountIn == amount_in
    assert event.amountOut == amount_out
    assert event.rewards == rewards
    # assert tx.return_value == (amount_in, amount_out)  # TODO: fix


def test_manager_burn__deposits_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    manager,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    mint_position_with_WETH9,
):
    zero_for_one = (
        token0_with_WETH9.address == WETH9.address
    )  # margin in token1 if true
    token_id = mint_position_with_WETH9(zero_for_one)

    position_id = pool_with_WETH9_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_with_WETH9_initialized_with_liquidity.positions(key)

    rewards = position.rewards
    amount_in = position.debt0 if zero_for_one else position.debt1
    amount_out = position.size + position.margin

    token_in = token0_with_WETH9 if zero_for_one else token1_with_WETH9
    token_out = token1_with_WETH9 if zero_for_one else token0_with_WETH9
    assert token_in.address == WETH9.address

    amount_in = position.debt0 if zero_for_one else position.debt1
    amount_out = position.size + position.margin

    balance_in_sender = token_in.balanceOf(sender.address)
    balance_in_pool = token_in.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )

    balance_out_alice = token_out.balanceOf(alice.address)
    balance_out_pool = token_out.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )

    balancee_alice = alice.balance
    balancee_pool = pool_with_WETH9_initialized_with_liquidity.balance

    balancee_sender = sender.balance
    balancee_WETH9 = WETH9.balance

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_with_WETH9_initialized_with_liquidity.token0(),
        pool_with_WETH9_initialized_with_liquidity.token1(),
        pool_with_WETH9_initialized_with_liquidity.maintenance(),
        pool_with_WETH9_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    value = (amount_in * 101) // 100  # add a bit extra to check refund ETH
    tx = manager.burn(burn_params, sender=sender, value=value)

    assert token_out.balanceOf(alice.address) == balance_out_alice + amount_out
    assert (
        token_in.balanceOf(sender.address) == balance_in_sender
    )  # no change since send in ETH

    assert (
        token_out.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance_out_pool - amount_out
    )
    assert (
        token_in.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance_in_pool + amount_in
    )

    assert alice.balance == balancee_alice + rewards
    assert pool_with_WETH9_initialized_with_liquidity.balance == balancee_pool - rewards
    assert (
        sender.balance == balancee_sender - amount_in - tx.gas_used * tx.gas_price
    )  # excess value refunded so only debt kept
    assert WETH9.balance == balancee_WETH9 + amount_in
    assert manager.balance == 0


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__reverts_when_not_owner(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    with reverts(manager.Unauthorized):
        manager.burn(burn_params, sender=alice)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    deadline = chain.pending_timestamp - 1
    burn_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    with reverts("Transaction too old"):
        manager.burn(burn_params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_burn__reverts_when_invalid_pool_key(
    rando_pool,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    deadline = chain.pending_timestamp + 3600
    burn_params = (
        rando_pool.token0(),
        rando_pool.token1(),
        rando_pool.maintenance(),
        rando_pool.oracle(),
        token_id,
        alice.address,
        deadline,
    )
    with reverts(manager.InvalidPoolKey):
        manager.burn(burn_params, sender=sender)
