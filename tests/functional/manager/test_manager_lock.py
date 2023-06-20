import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


# TODO: transfers funds


@pytest.fixture
def mint_position(pool_initialized_with_liquidity, chain, manager, sender):
    def mint(zero_for_one: bool) -> int:
        state = pool_initialized_with_liquidity.state()
        maintenance = pool_initialized_with_liquidity.maintenance()

        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )
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
        tx = manager.mint(mint_params, sender=sender)
        token_id, _ = tx.return_value
        return int(token_id)

    yield mint


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__adjusts_position(
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

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        token_id,
        margin_in,
        alice.address,
        deadline,
    )
    manager.lock(lock_params, sender=sender)

    state = pool_initialized_with_liquidity.state()
    tick_cumulative_last = state.tickCumulative
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position, tick_cumulative_last, oracle_tick_cumulatives[0], FUNDING_PERIOD
    )

    position.margin += margin_in
    assert pool_initialized_with_liquidity.positions(key) == position
    assert manager.positions(token_id) == (
        pool_initialized_with_liquidity.address,
        position_id,
        *position,
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__emits_lock(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__deposits_weth(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__reverts_when_not_owner(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_lock__reverts_when_invalid_pool_key(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
):
    pass
