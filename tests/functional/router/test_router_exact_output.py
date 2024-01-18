import pytest

from ape import reverts
from eth_abi.packed import encode_packed
from hexbytes import HexBytes
from math import sqrt

from utils.constants import MIN_SQRT_RATIO
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
)


@pytest.fixture
def pool_two_initialized_with_liquidity(
    pool_two,
    sqrt_price_x96_initial,
    spot_liquidity,
    callee,
    router,
    token0,
    token1,
    sender,
):
    # add liquidity
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(pool_two.address, sender.address, liquidity_delta, sender=sender)
    pool_two.approve(pool_two.address, 2**256 - 1, sender=sender)
    pool_two.approve(router.address, 2**256 - 1, sender=sender)

    # initialize with price 10% lower than original pool for arb tests
    # by swapping through the pool
    state = pool_two.state()
    reserve0, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount1 = int(reserve1 * (sqrt(0.9) - 1))  # specified one out
    callee.swap(
        pool_two.address,
        sender.address,
        True,
        amount1,
        MIN_SQRT_RATIO + 1,
        sender=sender,
    )

    return pool_two


@pytest.fixture
def multi_path(mock_univ3_pool, token0, token1):
    # e.g. token_in => pool => token_out => pool_two => token_in
    def _multi_path(zero_for_one: bool) -> HexBytes:
        # zero_for_one == True: 0 => 1 => 0
        # zero_for_one == False: 1 => 0 => 1
        token_in = token0.address if zero_for_one else token1.address
        token_out = token1.address if zero_for_one else token0.address
        return encode_packed(
            [
                "address",  # token in 0
                "uint24",  # maintenance 0
                "address",  # oracle 0
                "address",  # token out 0 / token in 1
                "uint24",  # maintenance 1
                "address",  # oracle 1
                "address",  # token in 1
            ],
            [
                token_in,
                250000,
                mock_univ3_pool.address,
                token_out,
                500000,
                mock_univ3_pool.address,
                token_in,
            ],
        )

    return _multi_path


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output__updates_states(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    multi_path,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    state_two = pool_two_initialized_with_liquidity.state()

    fee = pool_initialized_with_liquidity.fee()
    fee_two = pool_two_initialized_with_liquidity.fee()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1

    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
    )
    router.exactOutput(params, sender=sender)

    # calculate amount in from pool 1 to be used as amount out to pool 2
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, (not zero_for_one), -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if not zero_for_one:
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

    # calculate amount in from pool 2
    amount_out_two = (
        amount1 if zero_for_one else amount0
    )  # > 0 since was amount_in to pool 1

    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity, state_two.sqrtPriceX96, zero_for_one, -amount_out_two
    )  # price change before fees
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        sqrt_price_x96_next_two,
    )

    # factor in fees
    if zero_for_one:
        fees0_two = swap_math_lib.swapFees(amount0_two, fee_two, True)
        amount0_two += fees0_two
    else:
        fees1_two = swap_math_lib.swapFees(amount1_two, fee_two, True)
        amount1_two += fees1_two

    # determine liquidity, sqrtPriceX96 after
    (
        liquidity_after_two,
        sqrt_price_x96_after_two,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        amount0_two,
        amount1_two,
    )
    tick_after_two = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after_two)

    result_two = pool_two_initialized_with_liquidity.state()

    assert result_two.liquidity == liquidity_after_two
    assert result_two.sqrtPriceX96 == sqrt_price_x96_after_two
    assert result_two.tick == tick_after_two


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output__transfers_funds(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    token0,
    token1,
    multi_path,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    state_two = pool_two_initialized_with_liquidity.state()

    fee = pool_initialized_with_liquidity.fee()
    fee_two = pool_two_initialized_with_liquidity.fee()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1

    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # cache balances before swap
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_pool_two = token0.balanceOf(pool_two_initialized_with_liquidity.address)
    balance1_pool_two = token1.balanceOf(pool_two_initialized_with_liquidity.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
    )
    router.exactOutput(params, sender=sender)

    # calculate amount in from pool 1 to be used as amount out to pool 2
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, (not zero_for_one), -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if not zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    # calculate amount in from pool 2
    amount_out_two = (
        amount1 if zero_for_one else amount0
    )  # > 0 since was amount_in to pool 1
    amount_in = amount_out_two

    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity, state_two.sqrtPriceX96, zero_for_one, -amount_out_two
    )  # price change before fees
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        sqrt_price_x96_next_two,
    )

    # factor in fees
    if zero_for_one:
        fees0_two = swap_math_lib.swapFees(amount0_two, fee_two, True)
        amount0_two += fees0_two
    else:
        fees1_two = swap_math_lib.swapFees(amount1_two, fee_two, True)
        amount1_two += fees1_two

    amount_in_two = amount0_two if zero_for_one else amount1_two

    balance0_sender_after = (
        balance0_sender - amount_in_two if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in_two
    )

    assert token0.balanceOf(sender.address) == balance0_sender_after
    assert token1.balanceOf(sender.address) == balance1_sender_after

    balance0_alice_after = (
        balance0_alice + amount_out if zero_for_one else balance0_alice
    )
    balance1_alice_after = (
        balance1_alice if zero_for_one else balance1_alice + amount_out
    )

    assert token0.balanceOf(alice.address) == balance0_alice_after
    assert token1.balanceOf(alice.address) == balance1_alice_after

    balance0_pool_after = (
        balance0_pool + amount_in if (not zero_for_one) else balance0_pool - amount_out
    )
    balance1_pool_after = (
        balance1_pool - amount_out if (not zero_for_one) else balance1_pool + amount_in
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address) == balance0_pool_after
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address) == balance1_pool_after
    )

    balance0_pool_two_after = (
        balance0_pool_two - amount_out_two
        if (not zero_for_one)
        else balance0_pool_two + amount_in_two
    )
    balance1_pool_two_after = (
        balance1_pool_two + amount_in_two
        if (not zero_for_one)
        else balance1_pool_two - amount_out_two
    )

    assert (
        token0.balanceOf(pool_two_initialized_with_liquidity.address)
        == balance0_pool_two_after
    )
    assert (
        token1.balanceOf(pool_two_initialized_with_liquidity.address)
        == balance1_pool_two_after
    )


@pytest.mark.skip
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output__returns_amount_in(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    multi_path,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    # TODO: implement once fix tx.return_value issues
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    multi_path,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()

    deadline = chain.pending_timestamp - 1
    amount_in_max = 2**256 - 1
    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve1 // 100 if zero_for_one else 1 * reserve0 // 100

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
    )
    with reverts("Transaction too old"):
        router.exactOutput(params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_output__reverts_when_amount_in_greater_than_max(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    multi_path,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    state = pool_initialized_with_liquidity.state()
    state_two = pool_two_initialized_with_liquidity.state()

    fee = pool_initialized_with_liquidity.fee()
    fee_two = pool_two_initialized_with_liquidity.fee()

    deadline = chain.pending_timestamp + 3600

    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # calculate amount in from pool 1 to be used as amount out to pool 2
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity, state.sqrtPriceX96, (not zero_for_one), -amount_out
    )  # price change before fees
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # factor in fees
    if not zero_for_one:
        fees0 = swap_math_lib.swapFees(amount0, fee, True)
        amount0 += fees0
    else:
        fees1 = swap_math_lib.swapFees(amount1, fee, True)
        amount1 += fees1

    # calculate amount in from pool 2
    amount_out_two = (
        amount1 if zero_for_one else amount0
    )  # > 0 since was amount_in to pool 1

    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity, state_two.sqrtPriceX96, zero_for_one, -amount_out_two
    )  # price change before fees
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        sqrt_price_x96_next_two,
    )

    # factor in fees
    if zero_for_one:
        fees0_two = swap_math_lib.swapFees(amount0_two, fee_two, True)
        amount0_two += fees0_two
    else:
        fees1_two = swap_math_lib.swapFees(amount1_two, fee_two, True)
        amount1_two += fees1_two

    amount_in_two = amount0_two if zero_for_one else amount1_two

    amount_in_max = amount_in_two - 1
    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
    )
    with reverts("Too much requested"):
        router.exactOutput(params, sender=sender)
