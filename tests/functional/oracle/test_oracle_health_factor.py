import pytest

from utils.constants import (
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    SECONDS_AGO,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity, chain, position_lib, manager, sender
):
    def mint(zero_for_one: bool, size: int) -> int:
        maintenance = pool_initialized_with_liquidity.maintenance()
        oracle = pool_initialized_with_liquidity.oracle()

        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        margin = (size * maintenance * 200) // (MAINTENANCE_UNIT * 100)
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
def oracle_next_obs(rando_univ3_observations):
    def _oracle_next_obs(factor: int):
        obs_last = rando_univ3_observations[-1]
        obs_before = rando_univ3_observations[-2]
        tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

        obs_timestamp = obs_last[0] + SECONDS_AGO
        obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * factor) // 10000
        obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
        obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
        return obs

    return _oracle_next_obs


@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize(
    "tick_factor",
    [9000, 9500, 9900, 9950, 9980, 10000, 10020, 10050, 10100, 10500, 11000],
)
def test_oracle_health_factor__returns_health_factor(
    oracle_lens,
    manager,
    pool_initialized_with_liquidity,
    mock_univ3_pool,
    oracle_sqrt_price_initial_x96,
    sender,
    chain,
    zero_for_one,
    tick_factor,
    mint_position,
    oracle_next_obs,
):
    state = pool_initialized_with_liquidity.state()

    # change the oracle price
    obs = oracle_next_obs(tick_factor)
    mock_univ3_pool.pushObservation(*obs, sender=sender)

    pool_key = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
    )
    (_, oracle_sqrt_price_x96, __) = oracle_lens.sqrtPricesX96(pool_key)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0
    size = reserve * 1 // 100  # 1% of reserves

    token_id = mint_position(zero_for_one, size)
    position = manager.positions(token_id)

    maintenance = pool_initialized_with_liquidity.maintenance()
    debt_adjusted = (
        (maintenance + MAINTENANCE_UNIT) * position.debt
    ) // MAINTENANCE_UNIT
    collateral = position.size + position.margin

    debt_adjusted_in_margin = (
        (debt_adjusted * (oracle_sqrt_price_x96**2)) // (1 << 192)
        if position.zeroForOne
        else (debt_adjusted * (1 << 192)) // (oracle_sqrt_price_x96**2)
    )

    health_factor = (int(1e18) * collateral) // debt_adjusted_in_margin
    result = oracle_lens.healthFactor(token_id)

    assert pytest.approx(result, rel=1e-5) == health_factor
    assert position.safe == (result >= int(1e18))
    assert (position.margin >= position.safeMarginMinimum) == (result >= int(1e18))


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_oracle_health_factor__returns_health_factor_when_liquidation_sqrt_price_x96(
    oracle_lens,
    manager,
    pool_initialized_with_liquidity,
    mock_univ3_pool,
    oracle_sqrt_price_initial_x96,
    sender,
    chain,
    zero_for_one,
    mint_position,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    pool_key = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        maintenance,
        pool_initialized_with_liquidity.oracle(),
    )
    (_, oracle_sqrt_price_x96, __) = oracle_lens.sqrtPricesX96(pool_key)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0
    size = reserve * 1 // 100  # 1% of reserves

    token_id = mint_position(zero_for_one, size)
    position = manager.positions(token_id)
    liquidation_sqrt_price_x96 = oracle_lens.liquidationSqrtPriceX96(token_id)

    result = oracle_lens.healthFactor(
        position.zeroForOne,
        position.size,
        position.debt,
        position.margin,
        maintenance,
        liquidation_sqrt_price_x96,
    )
    assert pytest.approx(result, rel=1e-5) == int(1e18)
