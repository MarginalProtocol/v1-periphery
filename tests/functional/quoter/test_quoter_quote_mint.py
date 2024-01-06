import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FEE,
    REWARD,
    SECONDS_AGO,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def get_oracle_next_obs(rando_univ3_observations):
    def oracle_next_obs(tick_next: int) -> tuple:
        obs_last = rando_univ3_observations[-1]
        obs_timestamp = obs_last[0] + SECONDS_AGO
        obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick_next)
        obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
        obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
        return obs

    yield oracle_next_obs


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_mint__quotes_mint(
    pool_initialized_with_liquidity,
    quoter,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
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

    # quote first before state change
    result = quoter.quoteMint(mint_params)

    # actually mint and check result same as quote
    manager.mint(mint_params, sender=sender)

    id = 0  # starts at 0 for pool
    next_id = 1  # starts at 1 for nft position manager
    position = manager.positions(next_id)

    assert result.size == position.size
    assert result.debt == position.debt
    assert result.safe is True

    fees = position_lib.fees(position.size, FEE)
    rewards = position_lib.liquidationRewards(position.size, REWARD)
    amount_in = position.margin + rewards + fees
    assert result.amountIn == amount_in

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96

    key = get_position_key(manager.address, id)
    info = pool_initialized_with_liquidity.positions(key)
    margin_min = position_lib.marginMinimum(info, maintenance)
    assert (
        result.safeMarginMinimum == margin_min
    )  # oracle tick == pool tick in conftest.py


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_mint__quotes_mint_with_oracle_tick_near_liquidation(
    pool_initialized_with_liquidity,
    quoter,
    manager,
    mock_univ3_pool,
    zero_for_one,
    sender,
    chain,
    position_lib,
    get_oracle_next_obs,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    # push oracle observation so headed toward liquidation
    tick_next = (
        state.tick + 10 if zero_for_one else state.tick - 10
    )  # oracle 10 bps closer to liq than pool
    obs = get_oracle_next_obs(tick_next)
    mock_univ3_pool.pushObservation(*obs, sender=sender)

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
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

    # quote first before state change
    result = quoter.quoteMint(mint_params)

    # actually mint and check result same as quote
    manager.mint(mint_params, sender=sender)

    id = 0  # starts at 0 for pool ID
    key = get_position_key(manager.address, id)
    info = pool_initialized_with_liquidity.positions(key)
    info.tick = tick_next
    safe_margin_min = position_lib.marginMinimum(info, maintenance)
    assert (
        result.safeMarginMinimum == safe_margin_min
    )  # oracle tick == pool tick in conftest.py


# TODO: test revert statements
