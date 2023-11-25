import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FEE,
    REWARD,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


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

    next_id = 1  # starts at 1 for nft position manager
    position = manager.positions(next_id)
    assert result.size == position.size
    assert result.debt == position.debt

    fees = position_lib.fees(position.size, FEE)
    rewards = position_lib.liquidationRewards(position.size, REWARD)
    amount_in = position.margin + rewards + fees
    assert result.amountIn == amount_in

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96


# TODO: test revert statements
