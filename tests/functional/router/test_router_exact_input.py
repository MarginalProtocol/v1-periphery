import pytest

from ape import reverts
from eth_abi.packed import encode_packed
from hexbytes import HexBytes
from math import sqrt
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
    # initialize with price 10% lower than original pool for arb tests
    sqrt_price_x96 = int(sqrt(0.9) * sqrt_price_x96_initial)
    pool_two.initialize(sqrt_price_x96, sender=sender)

    # add liquidity
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(pool_two.address, sender.address, liquidity_delta, sender=sender)
    pool_two.approve(pool_two.address, 2**256 - 1, sender=sender)
    pool_two.approve(router.address, 2**256 - 1, sender=sender)
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
def test_router_exact_input__updates_states(
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
    amount_out_min = 0
    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
    )
    router.exactInput(params, sender=sender)

    # calculate amount out from pool 1 to be used as amount in to pool 2
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,  # token_in => token_out
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    # fees on amount in
    fees = amount_in - amount_in_less_fee
    fees0 = fees if zero_for_one else 0
    fees1 = 0 if zero_for_one else fees

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity, sqrt_price_x96_next, fees0, fees1
    )
    tick_after = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == liquidity_after
    assert result.sqrtPriceX96 == sqrt_price_x96_after
    assert result.tick == tick_after

    # calculate amount out from pool 2
    amount_in_two = amount_out
    amount_in_two_less_fee = amount_in_two - swap_math_lib.swapFees(
        amount_in_two, fee_two
    )
    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        (not zero_for_one),  # token_out => token_in
        amount_in_two_less_fee,
    )  # price change before fees added

    # fees on amount in
    fees_two = amount_in_two - amount_in_two_less_fee
    fees0_two = fees_two if (not zero_for_one) else 0
    fees1_two = 0 if (not zero_for_one) else fees_two

    (
        liquidity_after_two,
        sqrt_price_x96_after_two,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state_two.liquidity, sqrt_price_x96_next_two, fees0_two, fees1_two
    )
    tick_after_two = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after_two)

    result_two = pool_two_initialized_with_liquidity.state()
    assert result_two.liquidity == liquidity_after_two
    assert result_two.sqrtPriceX96 == sqrt_price_x96_after_two
    assert result_two.tick == tick_after_two


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input__transfers_funds(
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
    amount_out_min = 0
    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

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
        amount_in,
        amount_out_min,
    )
    router.exactInput(params, sender=sender)

    # calculate amount out from pool 1 to be used as amount in to pool 2
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,  # token_in => token_out
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    # check pool 1 balances
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

    # calculate amount out from pool 2
    amount_in_two = amount_out
    amount_in_two_less_fee = amount_in_two - swap_math_lib.swapFees(
        amount_in_two, fee_two
    )
    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        (not zero_for_one),  # token_out => token_in
        amount_in_two_less_fee,
    )  # price change before fees added
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity, state_two.sqrtPriceX96, sqrt_price_x96_next_two
    )
    amount_out_two = -amount1_two if (not zero_for_one) else -amount0_two

    # check pool 2 balances
    balance0_pool_two_after = (
        balance0_pool_two + amount_in_two
        if (not zero_for_one)
        else balance0_pool_two - amount_out_two
    )
    balance1_pool_two_after = (
        balance1_pool_two - amount_out_two
        if (not zero_for_one)
        else balance1_pool_two + amount_in_two
    )
    assert (
        token0.balanceOf(pool_two_initialized_with_liquidity.address)
        == balance0_pool_two_after
    )
    assert (
        token1.balanceOf(pool_two_initialized_with_liquidity.address)
        == balance1_pool_two_after
    )

    # check sender balances after
    balance0_sender_after = (
        balance0_sender - amount_in if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in
    )
    assert token0.balanceOf(sender.address) == balance0_sender_after
    assert token1.balanceOf(sender.address) == balance1_sender_after

    # check alice balances after
    balance0_alice_after = (
        balance0_alice if (not zero_for_one) else balance0_alice + amount_out_two
    )
    balance1_alice_after = (
        balance1_alice + amount_out_two if (not zero_for_one) else balance1_alice
    )
    assert token0.balanceOf(alice.address) == balance0_alice_after
    assert token1.balanceOf(alice.address) == balance1_alice_after


@pytest.mark.skip
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input__returns_amount_out(
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
    amount_out_min = 0
    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
    )
    tx = router.exactInput(params, sender=sender)

    # calculate amount out from pool 1 to be used as amount in to pool 2
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,  # token_in => token_out
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    # calculate amount out from pool 2
    amount_in_two = amount_out
    amount_in_two_less_fee = amount_in_two - swap_math_lib.swapFees(
        amount_in_two, fee_two
    )
    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        (not zero_for_one),  # token_out => token_in
        amount_in_two_less_fee,
    )  # price change before fees added
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity, state_two.sqrtPriceX96, sqrt_price_x96_next_two
    )
    amount_out_two = -amount1_two if (not zero_for_one) else -amount0_two
    assert tx.return_value == amount_out_two  # TODO: fix


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input__reverts_when_past_deadline(
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
    amount_out_min = 0
    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
    )

    with reverts("Transaction too old"):
        router.exactInput(params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_router_exact_input__reverts_when_amount_out_less_than_min(
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
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # calculate amount out from pool 1 to be used as amount in to pool 2
    amount_in_less_fee = amount_in - swap_math_lib.swapFees(amount_in, fee)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,  # token_in => token_out
        amount_in_less_fee,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    # calculate amount out from pool 2
    amount_in_two = amount_out
    amount_in_two_less_fee = amount_in_two - swap_math_lib.swapFees(
        amount_in_two, fee_two
    )
    sqrt_price_x96_next_two = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state_two.liquidity,
        state_two.sqrtPriceX96,
        (not zero_for_one),  # token_out => token_in
        amount_in_two_less_fee,
    )  # price change before fees added
    (amount0_two, amount1_two) = swap_math_lib.swapAmounts(
        state_two.liquidity, state_two.sqrtPriceX96, sqrt_price_x96_next_two
    )
    amount_out_two = -amount1_two if (not zero_for_one) else -amount0_two

    amount_out_min = amount_out_two + 1
    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
    )

    with reverts("Too little received"):
        router.exactInput(params, sender=sender)
