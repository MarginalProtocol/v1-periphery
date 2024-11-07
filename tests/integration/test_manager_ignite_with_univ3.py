import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    TICK_CUMULATIVE_RATE_MAX,
    FUNDING_PERIOD,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def mint_position(
    mrglv1_pool_initialized_with_liquidity,
    position_lib,
    chain,
    mrglv1_manager,
    sender,
):
    def mint(zero_for_one: bool) -> int:
        state = mrglv1_pool_initialized_with_liquidity.state()
        maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()
        oracle = mrglv1_pool_initialized_with_liquidity.oracle()

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
            mrglv1_pool_initialized_with_liquidity.token0(),
            mrglv1_pool_initialized_with_liquidity.token1(),
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

        premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()
        base_fee = chain.blocks[-1].base_fee
        rewards = position_lib.liquidationRewards(
            base_fee,
            BASE_FEE_MIN,
            GAS_LIQUIDATE,
            premium,
        )

        tx = mrglv1_manager.mint(mint_params, sender=sender, value=rewards)
        token_id = tx.decode_logs(mrglv1_manager.Mint)[0].tokenId
        return int(token_id)

    yield mint


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_ignite_with_univ3__settles_position(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_manager,
    univ3_pool,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
    position_amounts_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = mrglv1_pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(mrglv1_manager.address, position_id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    block_timestamp_next = chain.pending_timestamp
    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
        mrglv1_pool_initialized_with_liquidity.maintenance(),
        mrglv1_pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        alice.address,
        deadline,
    )
    mrglv1_manager.ignite(ignite_params, sender=sender)

    state = mrglv1_pool_initialized_with_liquidity.state()
    tick_cumulative_last = state.tickCumulative
    oracle_tick_cumulatives, _ = univ3_pool.observe([0])

    # sync then settle position
    position = position_lib.sync(
        position,
        block_timestamp_next,
        tick_cumulative_last,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    position = position_lib.settle(position)
    assert mrglv1_pool_initialized_with_liquidity.positions(key) == position


@pytest.mark.integration
def test_manager_ignite_with_univ3__withdraws_WETH9(
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_manager,
    WETH9,
    univ3_pool,
    sender,
    alice,
    chain,
    position_lib,
    position_amounts_lib,
    sqrt_price_math_lib,
    swap_math_lib,
    mint_position,
):
    zero_for_one = mrglv1_pool_initialized_with_liquidity.token1() == WETH9.address
    token_id = mint_position(zero_for_one)

    position = mrglv1_manager.positions(token_id)
    rewards = position.rewards

    spot_slot0 = univ3_pool.slot0()
    spot_liquidity = univ3_pool.liquidity()
    spot_fee = univ3_pool.fee()

    amount_in = position.debt
    amount_out = position.size + position.margin

    # calculate amount out from spot pool to subtract from amount_out
    amount_specified = -amount_in
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        (not zero_for_one),  # if debt in is 0 to marginal, need 0 out from spot
        amount_specified,
    )

    (spot_amount0, spot_amount1) = swap_math_lib.swapAmounts(
        spot_liquidity,
        spot_slot0.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    if zero_for_one:
        # zero debt into marginal means zero taken out of spot pool to repay (1 into spot)
        spot_amount1 += swap_math_lib.swapFees(spot_amount1, spot_fee, True)
    else:
        # one debt into marginal means one taken out of spot pool to repay (0 into spot)
        spot_amount0 += swap_math_lib.swapFees(spot_amount0, spot_fee, True)

    spot_amount_in = spot_amount1 if zero_for_one else spot_amount0

    # adjust amount out based off spot swap amount in required to repay debt
    # @dev should now include liquidation rewards converted to WETH9
    amount_out_recipient = amount_out - spot_amount_in + rewards

    # cache balances before ignite
    balancee_alice = alice.balance
    balancee_pool = mrglv1_pool_initialized_with_liquidity.balance

    balance_WETH9_pool = WETH9.balanceOf(mrglv1_pool_initialized_with_liquidity.address)
    balance_WETH9_spot = WETH9.balanceOf(univ3_pool.address)
    balance_WETH9_alice = WETH9.balanceOf(alice.address)

    block_timestamp_next = chain.pending_timestamp
    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0

    ignite_params = (
        mrglv1_pool_initialized_with_liquidity.token0(),
        mrglv1_pool_initialized_with_liquidity.token1(),
        mrglv1_pool_initialized_with_liquidity.maintenance(),
        mrglv1_pool_initialized_with_liquidity.oracle(),
        token_id,
        amount_out_min,
        mrglv1_manager.address,  # recipient is manager then unwrap to alice
        deadline,
    )
    calldata = [
        mrglv1_manager.ignite.as_transaction(ignite_params, sender=sender).data,
        mrglv1_manager.unwrapWETH9.as_transaction(
            amount_out_min, alice.address, sender=sender
        ).data,
    ]
    mrglv1_manager.multicall(calldata, sender=sender)

    balancee_alice_after = alice.balance
    balancee_pool_after = mrglv1_pool_initialized_with_liquidity.balance
    balance_WETH9_pool_after = WETH9.balanceOf(
        mrglv1_pool_initialized_with_liquidity.address
    )
    balance_WETH9_spot_after = WETH9.balanceOf(univ3_pool.address)
    balance_WETH9_alice_after = WETH9.balanceOf(alice.address)

    assert (
        pytest.approx(balance_WETH9_pool_after, rel=1e-9)
        == balance_WETH9_pool - amount_out
    )
    assert (
        pytest.approx(balance_WETH9_spot_after, rel=1e-9)
        == balance_WETH9_spot + spot_amount_in
    )
    assert balance_WETH9_alice_after == balance_WETH9_alice
    assert pytest.approx(balancee_pool_after, rel=1e-9) == balancee_pool - rewards
    assert (
        pytest.approx(balancee_alice_after, rel=1e-9)
        == balancee_alice + amount_out_recipient
    )
