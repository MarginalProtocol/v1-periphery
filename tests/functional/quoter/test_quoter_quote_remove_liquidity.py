import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


def test_quoter_quote_remove_liquidity__quotes_liquidity_remove(
    pool_initialized_with_liquidity,
    quoter,
    router,
    manager,
    sender,
    alice,
    chain,
    token0,
    token1,
    liquidity_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    liquidity = state.liquidity

    shares = shares_sender // 2
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    # cache balances of tokens prior
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteRemoveLiquidity(params)

    # actually remove liquidity and check result same as quote
    router.removeLiquidity(params, sender=sender)

    amount0 = token0.balanceOf(alice.address) - balance0_alice
    amount1 = token1.balanceOf(alice.address) - balance1_alice
    assert result.amount0 == amount0
    assert result.amount1 == amount1

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityDelta == liquidity - state.liquidity
    assert result.liquidityAfter == state.liquidity


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_remove_liquidity__quotes_liquidity_remove_when_liquidity_locked(
    pool_initialized_with_liquidity,
    quoter,
    router,
    manager,
    sender,
    alice,
    chain,
    zero_for_one,
    token0,
    token1,
    liquidity_math_lib,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    # mint a position first
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
    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee
    value = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )
    manager.mint(mint_params, sender=sender, value=value)
    assert pool_initialized_with_liquidity.state().totalPositions > 0

    # now quote remove liquidity
    state = pool_initialized_with_liquidity.state()
    shares_sender = pool_initialized_with_liquidity.balanceOf(sender.address)
    liquidity = state.liquidity

    shares = shares_sender // 2
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    # cache balances of tokens prior
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        shares,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteRemoveLiquidity(params)

    # actually remove liquidity and check result same as quote
    router.removeLiquidity(params, sender=sender)

    amount0 = token0.balanceOf(alice.address) - balance0_alice
    amount1 = token1.balanceOf(alice.address) - balance1_alice
    assert result.amount0 == amount0
    assert result.amount1 == amount1

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityDelta == liquidity - state.liquidity
    assert result.liquidityAfter == state.liquidity


# TODO: test revert cases
