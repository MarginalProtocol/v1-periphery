import pytest

from ape import reverts
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__updates_state(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    router.exactOutputSingle(params, sender=sender)

    # calculate liquidity, sqrtPriceX96 update
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    # determine liquidity, sqrtPriceX96 after
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )
    tick_after = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == liquidity_after
    assert result.sqrtPriceX96 == sqrt_price_x96_after
    assert result.tick == tick_after


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__transfers_funds(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    token0,
    token1,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    # cache balances before swap
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    router.exactOutputSingle(params, sender=sender)

    # calculate amount in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    amount_in = amount0 if zero_for_one else amount1

    balance0_sender_after = (
        balance0_sender - amount_in if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in
    )

    assert token0.balanceOf(sender.address) == balance0_sender_after
    assert token1.balanceOf(sender.address) == balance1_sender_after

    balance0_alice_after = (
        balance0_alice if zero_for_one else balance0_alice + amount_out
    )
    balance1_alice_after = (
        balance1_alice + amount_out if zero_for_one else balance1_alice
    )

    assert token0.balanceOf(alice.address) == balance0_alice_after
    assert token1.balanceOf(alice.address) == balance1_alice_after

    balance0_pool_after = (
        balance0_pool + amount_in if zero_for_one else balance0_pool - amount_out
    )
    balance1_pool_after = (
        balance1_pool - amount_out if zero_for_one else balance1_pool + amount_in
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address) == balance0_pool_after
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address) == balance1_pool_after
    )


def test_router_exact_output_single__deposits_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_with_WETH9_initialized_with_liquidity.state()
    fee = pool_with_WETH9_initialized_with_liquidity.fee()
    oracle = pool_with_WETH9_initialized_with_liquidity.oracle()

    # set WETH9 allowance to zero to ensure all payment in ETH
    WETH9.approve(router.address, 0, sender=sender)

    # WETH9 in to test ETH deposits
    token_in = WETH9
    token_out = (
        token0_with_WETH9
        if token0_with_WETH9.address != WETH9.address
        else token1_with_WETH9
    )
    zero_for_one = token_in.address == token0_with_WETH9.address

    maintenance = pool_with_WETH9_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    # cache balances before swap
    balancei_sender = token_in.balanceOf(sender.address)
    balanceo_sender = token_out.balanceOf(sender.address)
    balancee_sender = sender.balance

    balancei_pool = token_in.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )
    balanceo_pool = token_out.balanceOf(
        pool_with_WETH9_initialized_with_liquidity.address
    )

    balancei_alice = token_in.balanceOf(alice.address)
    balanceo_alice = token_out.balanceOf(alice.address)

    balancee_WETH9 = WETH9.balance

    # calculate amount in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    amount_in = amount0 if zero_for_one else amount1

    params = (
        token_in.address,
        token_out.address,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    value = (amount_in * 101) // 100  # send excess ETH to test router refunds
    tx = router.exactOutputSingle(params, sender=sender, value=value)

    balancei_sender_after = balancei_sender  # since send in native ETH instead of WETH
    balanceo_sender_after = balanceo_sender  # since send out to alice

    assert token_in.balanceOf(sender.address) == balancei_sender_after
    assert token_out.balanceOf(sender.address) == balanceo_sender_after
    assert (
        sender.balance == balancee_sender - amount_in - tx.gas_used * tx.gas_price
    )  # router refunds excess ETH

    balancei_alice_after = balancei_alice
    balanceo_alice_after = balanceo_alice + amount_out

    assert token_in.balanceOf(alice.address) == balancei_alice_after
    assert token_out.balanceOf(alice.address) == balanceo_alice_after

    balancei_pool_after = balancei_pool + amount_in
    balanceo_pool_after = balanceo_pool - amount_out

    assert (
        token_in.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balancei_pool_after
    )
    assert (
        token_out.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balanceo_pool_after
    )
    assert router.balance == 0
    assert WETH9.balance == balancee_WETH9 + amount_in


@pytest.mark.skip
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__returns_amount_in(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    tx = router.exactOutputSingle(params, sender=sender)

    # calculate liquidity, sqrtPriceX96 update
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    amount_in = amount0 if zero_for_one else amount1
    assert tx.return_value == amount_in  # TODO: fix


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
):
    state = pool_initialized_with_liquidity.state()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp - 1
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )

    with reverts("Transaction too old"):
        router.exactOutputSingle(params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output_single__reverts_when_amount_in_greater_than_max(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    oracle = pool_initialized_with_liquidity.oracle()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )
    maintenance = pool_initialized_with_liquidity.maintenance()

    deadline = chain.pending_timestamp + 3600
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    # calculate liquidity, sqrtPriceX96 update
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, zero_for_one, -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    amount_in = amount0 if zero_for_one else amount1
    amount_in_max = amount_in - 1

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
        sqrt_price_limit_x96,
    )

    with reverts("Too much requested"):
        router.exactOutputSingle(params, sender=sender)
