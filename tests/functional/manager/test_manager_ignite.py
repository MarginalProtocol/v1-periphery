import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


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
