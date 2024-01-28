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
def spot_pool_initialized_with_liquidity(
    pool_initialized_with_liquidity,
    mock_univ3_pool,
    spot_liquidity,
    sqrt_price_x96_initial,
    token0,
    token1,
    sender,
):
    slot0 = mock_univ3_pool.slot0()
    slot0.sqrtPriceX96 = (
        pool_initialized_with_liquidity.state().sqrtPriceX96  # have prices coincide between spot and marginal
    )
    mock_univ3_pool.setSlot0(slot0, sender=sender)

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        spot_liquidity, slot0.sqrtPriceX96
    )
    token0.mint(mock_univ3_pool.address, reserve0, sender=sender)
    token1.mint(mock_univ3_pool.address, reserve1, sender=sender)
    mock_univ3_pool.setLiquidity(spot_liquidity, sender=sender)

    return mock_univ3_pool


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    position_lib,
    chain,
    manager,
    sender,
):
    def mint(zero_for_one: bool) -> int:
        state = pool_initialized_with_liquidity.state()
        maintenance = pool_initialized_with_liquidity.maintenance()
        oracle = pool_initialized_with_liquidity.oracle()

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
def test_quoter_quote_ignite__quotes_ignite(
    pool_initialized_with_liquidity,
    spot_pool_initialized_with_liquidity,
    quoter,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    position = manager.positions(token_id)

    # forward the chain one funding period for debts after funding
    chain.mine(deltatime=FUNDING_PERIOD)

    assert manager.positions(token_id).debt != position.debt

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )

    # quote first before state change
    result = quoter.quoteIgnite(ignite_params)

    # actually ignite and check result same as quote
    tx = manager.ignite(ignite_params, sender=sender)
    events = tx.decode_logs(manager.Ignite)
    assert len(events) == 1
    event = events[0]

    assert result.amountOut == event.amountOut
    assert result.rewards == event.rewards

    state = pool_initialized_with_liquidity.state()
    assert result.liquidityAfter == state.liquidity
    assert result.sqrtPriceX96After == state.sqrtPriceX96

    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    assert result.liquidityLockedAfter == liquidity_locked


# TODO: test revert statements
