import pytest

from ape import reverts
from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


def test_quoter_quote_add_liquidity__quotes_liquidity_add(
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

    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    # cache balances of tokens prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteAddLiquidity(params)

    # actually add liquidity and check result same as quote
    router.addLiquidity(params, sender=sender)

    shares = pool_initialized_with_liquidity.balanceOf(alice.address) - shares_alice
    assert result.shares == shares

    amount0 = balance0_sender - token0.balanceOf(sender.address)
    amount1 = balance1_sender - token1.balanceOf(sender.address)
    assert result.amount0 == amount0
    assert result.amount1 == amount1

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_quoter_quote_add_liquidity__quotes_liquidity_add_when_liquidity_locked(
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

    # now quote add liquidity
    liquidity_delta_desired = (state.liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state.sqrtPriceX96
    )

    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    # cache balances of tokens prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteAddLiquidity(params)

    # actually add liquidity and check result same as quote
    router.addLiquidity(params, sender=sender)

    shares = pool_initialized_with_liquidity.balanceOf(alice.address) - shares_alice
    assert result.shares == shares

    amount0 = balance0_sender - token0.balanceOf(sender.address)
    amount1 = balance1_sender - token1.balanceOf(sender.address)
    assert result.amount0 == amount0
    assert result.amount1 == amount1

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity


def test_quoter_quote_add_liquidity__reverts_when_no_liquidity(
    pool_two,
    quoter,
    router,
    manager,
    sender,
    alice,
    chain,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    state = pool_two.state()
    assert state.initialized is False

    amount0_desired = spot_reserve0 * 1 // 100
    amount1_desired = spot_reserve1 * 1 // 100
    amount0_min = 0
    amount1_min = 0
    deadline = chain.pending_timestamp + 3600

    params = (
        pool_two.token0(),
        pool_two.token1(),
        pool_two.maintenance(),
        pool_two.oracle(),
        alice.address,
        amount0_desired,
        amount1_desired,
        amount0_min,
        amount1_min,
        deadline,
    )

    # quote first before state change
    with reverts("Pool not initialized"):
        quoter.quoteAddLiquidity(params)


# TODO: test revert statements
