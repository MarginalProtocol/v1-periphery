import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    SECONDS_AGO,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def mint_position(pool_initialized_with_liquidity, chain, manager, sender):
    def mint(zero_for_one: bool) -> int:
        state = pool_initialized_with_liquidity.state()
        maintenance = pool_initialized_with_liquidity.maintenance()

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
        deadline = chain.pending_timestamp + 3600

        mint_params = (
            pool_initialized_with_liquidity.token0(),
            pool_initialized_with_liquidity.token1(),
            maintenance,
            zero_for_one,
            size,
            size_min,
            sqrt_price_limit_x96,
            margin,
            sender.address,
            deadline,
        )
        tx = manager.mint(mint_params, sender=sender)
        token_id, _ = tx.return_value
        return int(token_id)

    yield mint


@pytest.fixture
def get_oracle_next_obs(rando_univ3_observations):
    def oracle_next_obs(zero_for_one: bool) -> tuple:
        obs_last = rando_univ3_observations[-1]
        obs_before = rando_univ3_observations[-2]
        tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

        tick_pc_change = 120 if zero_for_one else 80

        obs_timestamp = obs_last[0] + SECONDS_AGO
        obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * tick_pc_change) // 100
        obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
        obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
        return obs

    yield oracle_next_obs


@pytest.fixture
def adjust_oracle(mock_univ3_pool, sender, get_oracle_next_obs):
    def adjust(zero_for_one: bool):
        obs = get_oracle_next_obs(zero_for_one)
        mock_univ3_pool.pushObservation(*obs, sender=sender)

    yield adjust


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_grab__liquidates_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    alice,
    bob,
    chain,
    mock_univ3_pool,
    position_lib,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    adjust_oracle(zero_for_one)  # makes position unsafe

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        alice.address,
        deadline,
    )
    manager.grab(grab_params, sender=bob)

    state = pool_initialized_with_liquidity.state()
    tick_cumulative_last = state.tickCumulative
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])

    # sync then liquidate position
    position = position_lib.sync(
        position, tick_cumulative_last, oracle_tick_cumulatives[0], FUNDING_PERIOD
    )
    position = position_lib.liquidate(position)
    assert pool_initialized_with_liquidity.positions(key) == position


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_grab__transfers_funds(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    alice,
    bob,
    chain,
    token0,
    token1,
    position_lib,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    adjust_oracle(zero_for_one)  # makes position unsafe

    reward = pool_initialized_with_liquidity.reward()
    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    token_out = token0 if not zero_for_one else token1
    amount_out = position_lib.liquidationRewards(position.size, reward)

    balance_pool = token_out.balanceOf(pool_initialized_with_liquidity.address)
    balance_alice = token_out.balanceOf(alice.address)

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        alice.address,
        deadline,
    )
    manager.grab(grab_params, sender=bob)

    assert token_out.balanceOf(alice.address) == balance_alice + amount_out
    assert (
        token_out.balanceOf(pool_initialized_with_liquidity.address)
        == balance_pool - amount_out
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_grab__emits_grab(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    alice,
    bob,
    chain,
    position_lib,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    adjust_oracle(zero_for_one)  # makes position unsafe

    reward = pool_initialized_with_liquidity.reward()
    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    rewards = position_lib.liquidationRewards(position.size, reward)

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        alice.address,
        deadline,
    )
    tx = manager.grab(grab_params, sender=bob)
    events = tx.decode_logs(manager.Grab)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == token_id
    assert event.rewards == rewards
    assert tx.return_value == rewards


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_grab__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    alice,
    bob,
    chain,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    adjust_oracle(zero_for_one)  # makes position unsafe

    deadline = chain.pending_timestamp - 1
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        alice.address,
        deadline,
    )
    with reverts("Transaction too old"):
        manager.grab(grab_params, sender=bob)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_grab__reverts_when_invalid_pool_key(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    alice,
    bob,
    chain,
    mock_univ3_pool,
    position_lib,
    mint_position,
    adjust_oracle,
    rando_token_a_address,
):
    token_id = mint_position(zero_for_one)
    adjust_oracle(zero_for_one)  # makes position unsafe

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        rando_token_a_address,
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        alice.address,
        deadline,
    )
    with reverts(manager.InvalidPoolKey):
        manager.grab(grab_params, sender=bob)
