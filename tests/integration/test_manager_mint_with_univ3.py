import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    SECONDS_AGO,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint_with_univ3__opens_position(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_manager,
    univ3_pool,
    zero_for_one,
    sender,
    chain,
    oracle_lib,
    position_lib,
    position_amounts_lib,
    position_health_lib,
):
    state = mrglv1_pool_initialized_with_liquidity.state()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()
    oracle = mrglv1_pool_initialized_with_liquidity.oracle()

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
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
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

    premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = mrglv1_manager.mint(mint_params, sender=sender, value=rewards)

    oracle_tick_cumulatives, _ = univ3_pool.observe([SECONDS_AGO, 0])
    oracle_tick_cumulative = oracle_tick_cumulatives[1]
    state_tick_cumulative = (
        mrglv1_pool_initialized_with_liquidity.state().tickCumulative
    )
    tick_cumulative_delta = oracle_tick_cumulative - state_tick_cumulative

    oracle_tick_cumulative_delta = (
        oracle_tick_cumulatives[1] - oracle_tick_cumulatives[0]
    )
    oracle_sqrt_price_x96 = oracle_lib.oracleSqrtPriceX96(
        oracle_tick_cumulative_delta, SECONDS_AGO
    )

    events = tx.decode_logs(mrglv1_manager.Mint)
    assert len(events) == 1
    event = events[0]
    token_id = int(event.tokenId)

    position = mrglv1_manager.positions(token_id)
    assert position.positionId == token_id - 1
    assert position.size >= size_min
    assert position.margin == margin

    key = get_position_key(mrglv1_manager.address, position.positionId)
    info = mrglv1_pool_initialized_with_liquidity.positions(key)
    assert info.tickCumulativeDelta == tick_cumulative_delta

    health = position_health_lib.getHealthForPosition(
        info.zeroForOne,
        info.size,
        info.debt0 if info.zeroForOne else info.debt1,
        info.margin,
        maintenance,
        oracle_sqrt_price_x96,
    )
    assert position.health == health


@pytest.mark.integration
def test_manager_mint_with_univ3__deposits_weth(
    mrglv1_pool_initialized_with_liquidity,
    WETH9,
    mrglv1_manager,
    sender,
    chain,
    position_lib,
):
    state = mrglv1_pool_initialized_with_liquidity.state()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()
    oracle = mrglv1_pool_initialized_with_liquidity.oracle()
    fee = mrglv1_pool_initialized_with_liquidity.fee()

    zero_for_one = (
        mrglv1_pool_initialized_with_liquidity.token1() == WETH9.address
    )  # since want margin in WETH for test
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
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
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

    premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    fees = position_lib.fees(size, fee)
    value = margin + fees + rewards

    balancee_sender = sender.balance

    tx = mrglv1_manager.mint(mint_params, sender=sender, value=value)
    event = tx.decode_logs(mrglv1_manager.Mint)[0]
    token_id = event.tokenId
    assert token_id == 1  # token with ID 1 minted

    # check ETH balance reduced by margin + fees + rewards
    amount_in = event.margin + event.fees + event.rewards
    assert sender.balance == balancee_sender - amount_in - tx.gas_price * tx.gas_used


@pytest.mark.integration
def test_manager_mint_with_univ3__transfers_weth_when_value_rewards(
    mrglv1_pool_initialized_with_liquidity,
    WETH9,
    mrglv1_manager,
    sender,
    chain,
    position_lib,
):
    state = mrglv1_pool_initialized_with_liquidity.state()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()
    oracle = mrglv1_pool_initialized_with_liquidity.oracle()

    zero_for_one = (
        mrglv1_pool_initialized_with_liquidity.token1() == WETH9.address
    )  # since want margin in WETH for test
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
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
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

    premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    balancee_sender = sender.balance
    balancew_sender = WETH9.balanceOf(sender.address)

    tx = mrglv1_manager.mint(mint_params, sender=sender, value=rewards)
    event = tx.decode_logs(mrglv1_manager.Mint)[0]
    token_id = event.tokenId
    assert token_id == 1  # token with ID 1 minted

    # check WETH balance reduced by margin + fees
    amount_in = event.margin + event.fees
    assert WETH9.balanceOf(sender.address) == balancew_sender - amount_in

    # check ETH balance reduced by rewards
    assert (
        sender.balance == balancee_sender - event.rewards - tx.gas_used * tx.gas_price
    )
