import pytest
from math import sqrt

from hexbytes import HexBytes
from eth_abi.packed import encode_packed
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


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
def test_quoter_quote_exact_output__quotes_swap(
    pool_initialized_with_liquidity,
    pool_two_initialized_with_liquidity,
    quoter,
    router,
    manager,
    multi_path,
    zero_for_one,
    sender,
    alice,
    chain,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1

    path = multi_path(zero_for_one)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_out = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # cache balance of token out prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    params = (
        path,
        alice.address,  # recipient
        deadline,
        amount_out,
        amount_in_max,
    )

    # quote first before state change
    result = quoter.quoteExactOutput(params)

    # actually swap and check result same as quote
    router.exactOutput(params, sender=sender)

    # zero_for_one == True: 0 <= 1 <= 0
    # zero_for_one == False: 1 <= 0 <= 1
    amount_in = (
        balance0_sender - token0.balanceOf(sender.address)
        if zero_for_one
        else balance1_sender - token1.balanceOf(sender.address)
    )
    assert result.amountIn == amount_in

    # swap path: pool 1 <= pool 2
    assert len(result.liquiditiesAfter) == 2
    assert len(result.sqrtPricesX96After) == 2

    state = pool_initialized_with_liquidity.state()
    assert result.liquiditiesAfter[0] == state.liquidity
    assert result.sqrtPricesX96After[0] == state.sqrtPriceX96

    state_two = pool_two_initialized_with_liquidity.state()
    assert result.liquiditiesAfter[1] == state_two.liquidity
    assert result.sqrtPricesX96After[1] == state_two.sqrtPriceX96


# TODO: test revert statements
