import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    FUNDING_PERIOD,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def mint_position(
    mrglv1_pool_initialized_with_liquidity,
    position_lib,
    chain,
    mrglv1_manager,
    sender,
):
    def mint(zero_for_one: bool) -> int:
        state = mrglv1_pool_initialized_with_liquidity.state()
        maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()
        oracle = mrglv1_pool_initialized_with_liquidity.oracle()

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
        token_id = tx.decode_logs(mrglv1_manager.Mint)[0].tokenId
        return int(token_id)

    yield mint


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_ignite_with_univ3__settles_position(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_quoter,
    mrglv1_manager,
    univ3_pool,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    position_amounts_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    position = mrglv1_manager.positions(token_id)

    # forward the chain one funding period for debts after funding
    chain.mine(deltatime=FUNDING_PERIOD)
    assert mrglv1_manager.positions(token_id).debt != position.debt

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
        mrglv1_pool_initialized_with_liquidity.maintenance(),
        mrglv1_pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )

    # quote first before state change
    result = mrglv1_quoter.quoteIgnite(ignite_params)

    tx = mrglv1_manager.ignite(ignite_params, sender=sender)
    events = tx.decode_logs(mrglv1_manager.Ignite)
    assert len(events) == 1
    event = events[0]

    assert result.amountOut == event.amountOut
    assert result.rewards == event.rewards

    state = mrglv1_pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96

    liquidity_locked = mrglv1_pool_initialized_with_liquidity.liquidityLocked()
    assert result.liquidityLockedAfter == liquidity_locked
