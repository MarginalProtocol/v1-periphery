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


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_viewer_positions__returns_position(
    oracle_lens,
    position_viewer,
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
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0
    size = reserve * 1 // 100  # 1% of reserves

    token_id = mint_position(zero_for_one, size)
    position = manager.positions(token_id)

    result = position_viewer.positions(
        position.pool, manager.address, position.positionId
    )

    health_factor = oracle_lens.healthFactor(token_id)
    viewer_position = (
        position.zeroForOne,
        position.size,
        position.debt,
        position.margin,
        position.safeMarginMinimum,
        position.liquidated,
        position.safe,
        position.rewards,
        health_factor,
    )
    assert result == viewer_position
