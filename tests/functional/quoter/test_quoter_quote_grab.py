import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    FUNDING_PERIOD,
    SECONDS_AGO,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


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
def test_quoter_quote_grab__quotes_grab(
    pool_initialized_with_liquidity,
    quoter,
    manager,
    zero_for_one,
    sender,
    alice,
    bob,
    chain,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    position = manager.positions(token_id)

    # forward the chain one funding period for debts after funding
    chain.mine(deltatime=FUNDING_PERIOD)

    assert manager.positions(token_id).debt != position.debt

    # make position unsafe
    adjust_oracle(zero_for_one)
    position = manager.positions(token_id)
    assert position.safe is False

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteGrab(grab_params)

    # actually burn and check result same as quote
    tx = manager.grab(grab_params, sender=bob)
    events = tx.decode_logs(manager.Grab)
    assert len(events) == 1
    event = events[0]

    assert result.rewards == event.rewards

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96

    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    assert result.liquidityLockedAfter == liquidity_locked


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_grab__reverts_when_position_safe(
    pool_initialized_with_liquidity,
    quoter,
    manager,
    zero_for_one,
    sender,
    alice,
    bob,
    chain,
    mint_position,
    adjust_oracle,
):
    token_id = mint_position(zero_for_one)
    position = manager.positions(token_id)

    # check position safe
    position.safe is True

    deadline = chain.pending_timestamp + 3600
    grab_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        alice.address,
        deadline,
    )

    # quote first before state change
    with reverts("Position safe"):
        quoter.quoteGrab(grab_params)


# TODO: test revert statements
