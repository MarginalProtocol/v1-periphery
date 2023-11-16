import pytest

from ape import reverts
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__updates_state(
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    # calculate liquidity, sqrtPriceX96 update in slightly diff way than on-chain. check close
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in_less_fee,
    )  # price change before fees added

    # fees on amount in
    fees = amount_in - amount_in_less_fee
    amount0 = fees if zero_for_one else 0
    amount1 = 0 if zero_for_one else fees

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity, sqrt_price_x96_next, amount0, amount1
    )
    tick_after = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == liquidity_after
    assert result.sqrtPriceX96 == sqrt_price_x96_after
    assert result.tick == tick_after


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__transfers_funds(
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

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
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    # calculate amount out
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

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


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__returns_amount_out(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    tx = router.exactInputSingle(params, sender=sender)

    # calculate amount out
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0
    assert tx.return_value == amount_out


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__reverts_when_past_deadline(
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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )

    with reverts("Transaction too old"):
        router.exactInputSingle(params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input_single__reverts_when_amount_out_less_than_min(
    pool_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    sqrt_price_math_lib,
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
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # calculate amount out
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    amount_out_min = amount_out + 1
    params = (
        token_in,
        token_out,
        maintenance,
        oracle,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )

    with reverts("Too little received"):
        router.exactInputSingle(params, sender=sender)
