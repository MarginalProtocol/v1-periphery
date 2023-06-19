import pytest

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT, REWARD
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__opens_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    liquidity_delta = (state.liquidity * 5) // 100  # 5% borrowed for 1% size
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    amount = amount1 if zero_for_one else amount0

    size = int(
        (amount * maintenance)
        // (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    deadline = chain.pending_timestamp + 3600

    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    position.margin = margin
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    mint_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        maintenance,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        size_min,
        sender.address,
        deadline,
    )
    manager.mint(mint_params, sender=sender)

    owner = manager.address
    id = state.totalPositions
    key = get_position_key(owner, id)
    result = pool_initialized_with_liquidity.positions(key)
    assert result == position


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__mints_token(
    pool_initialized_with_liquidity, manager, zero_for_one, sender
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__sets_position_ref(
    pool_initialized_with_liquidity, manager, zero_for_one, sender
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__emits_mint(
    pool_initialized_with_liquidity, manager, zero_for_one, sender
):
    pass


# TODO: new pool with weth9
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__deposits_weth(zero_for_one, sender):
    pass


def test_manager_mint__reverts_when_past_deadline(
    pool_initialized_with_liquidity, manager, sender
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_size_less_than_min(
    pool_initialized_with_liquidity, manager, zero_for_one, sender
):
    pass
