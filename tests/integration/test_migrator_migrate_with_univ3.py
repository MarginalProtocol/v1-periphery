import pytest

from ape import reverts

from utils.constants import MAX_TICK
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def mint_univ3_lp_position(
    univ3_manager,
    univ3_pool,
    mrglv1_token0,
    mrglv1_token1,
    sender,
):
    def mint(tick_lower: int, tick_upper: int) -> int:
        sqrt_price_x96 = univ3_pool.slot0().sqrtPriceX96
        liquidity = univ3_pool.liquidity()

        liquidity_desired_full_range = (liquidity * 1) // 10000
        (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity_desired_full_range, sqrt_price_x96
        )

        params = (
            mrglv1_token0.address,
            mrglv1_token1.address,
            univ3_pool.fee(),
            tick_lower,
            tick_upper,
            amount0_desired,
            amount1_desired,
            0,
            0,
            sender.address,
            2**256 - 1,
        )
        tx = univ3_manager.mint(params, sender=sender)
        token_id = tx.decode_logs(univ3_manager.IncreaseLiquidity)[0].tokenId
        return int(token_id)

    yield mint


@pytest.mark.integration
def test_migrator_migrate_with_univ3__migrates_liquidity(
    mrglv1_migrator,
    mrglv1_router,
    univ3_manager,
    univ3_pool,
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_token0,
    mrglv1_token1,
    sender,
    alice,
    chain,
    mint_univ3_lp_position,
):
    slot0 = univ3_pool.slot0()
    tick_spacing = univ3_pool.tickSpacing()

    state = mrglv1_pool_initialized_with_liquidity.state()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()

    tick_upper = MAX_TICK - (MAX_TICK % tick_spacing)
    tick_lower = -tick_upper

    univ3_lp_token_id = mint_univ3_lp_position(tick_lower, tick_upper)
    univ3_lp_position = univ3_manager.positions(univ3_lp_token_id)

    # approve v1 migrator to operate with univ3 manager
    univ3_manager.approve(mrglv1_migrator.address, univ3_lp_token_id, sender=sender)

    # cache token balances prior
    balance0_univ3_pool = mrglv1_token0.balanceOf(univ3_pool.address)
    balance1_univ3_pool = mrglv1_token1.balanceOf(univ3_pool.address)

    balance0_mrglv1_pool = mrglv1_token0.balanceOf(
        mrglv1_pool_initialized_with_liquidity.address
    )
    balance1_mrglv1_pool = mrglv1_token1.balanceOf(
        mrglv1_pool_initialized_with_liquidity.address
    )

    balance0_sender = mrglv1_token0.balanceOf(sender.address)
    balance1_sender = mrglv1_token1.balanceOf(sender.address)

    shares_alice = mrglv1_pool_initialized_with_liquidity.balanceOf(alice.address)

    # migrate percentage of univ3 position to marginal v1 with rest to sender
    percentage_to_migrate = 50
    deadline = chain.pending_timestamp + 3600
    refund_as_eth = False
    params = (
        univ3_lp_token_id,
        univ3_lp_position.liquidity,  # liquidityToRemove
        0,  # amount{0,1}MinToRemove
        0,
        percentage_to_migrate,
        0,  # amount{0,1}MinToMigrate
        0,
        maintenance,
        alice.address,
        deadline,
        refund_as_eth,
    )
    tx = mrglv1_migrator.migrate(params, sender=sender)

    # decrease liquidity event on uni v3 manager
    events_decrease_liquidity = tx.decode_logs(univ3_manager.DecreaseLiquidity)
    assert len(events_decrease_liquidity) == 1
    event_univ3_manager = events_decrease_liquidity[0]

    # check liquidity liquidity removed is as expected
    liquidity_removed = univ3_lp_position.liquidity
    (amount0_removed, amount1_removed) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_removed, slot0.sqrtPriceX96
    )
    assert event_univ3_manager.liquidity == liquidity_removed
    assert (
        pytest.approx(event_univ3_manager.amount0, rel=1e-4, abs=1) == amount0_removed
    )
    assert (
        pytest.approx(event_univ3_manager.amount1, rel=1e-4, abs=1) == amount1_removed
    )

    assert (
        -event_univ3_manager.amount0
        == mrglv1_token0.balanceOf(univ3_pool.address) - balance0_univ3_pool
    )
    assert (
        -event_univ3_manager.amount1
        == mrglv1_token1.balanceOf(univ3_pool.address) - balance1_univ3_pool
    )

    # increase liquidity event on mrgl v1 router
    events_increase_liquidity = tx.decode_logs(mrglv1_router.IncreaseLiquidity)
    assert len(events_increase_liquidity) == 1
    event_mrglv1_router = events_increase_liquidity[0]

    # check alice minted shares
    shares_to_alice = (
        mrglv1_pool_initialized_with_liquidity.balanceOf(alice.address) - shares_alice
    )
    assert event_mrglv1_router.shares == shares_to_alice

    # calculate expected liquidity delta and amounts to marginal v1
    liquidity_to_migrate = (univ3_lp_position.liquidity * percentage_to_migrate) // 100
    (amount0_migrated, amount1_migrated) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_to_migrate, state.sqrtPriceX96
    )
    amount0_refunded = amount0_removed - amount0_migrated
    amount1_refunded = amount1_removed - amount1_migrated

    # compare with alice liquidity share of pool
    state_after = mrglv1_pool_initialized_with_liquidity.state()
    assert (
        pytest.approx(state_after.liquidity, rel=1e-4, abs=1)
        == state.liquidity + liquidity_to_migrate
    )

    total_shares = mrglv1_pool_initialized_with_liquidity.totalSupply()
    total_liquidity = (
        state.liquidity
        + liquidity_to_migrate
        + mrglv1_pool_initialized_with_liquidity.liquidityLocked()
    )
    liquidity_to_alice = (shares_to_alice * total_liquidity) // total_shares

    # TODO: fix calcs for lower rel tolerance levels below
    assert (
        pytest.approx(event_mrglv1_router.liquidityDelta, rel=1e-4, abs=1)
        == liquidity_to_alice
    )
    assert (
        pytest.approx(event_mrglv1_router.amount0, rel=1e-2, abs=1) == amount0_migrated
    )
    assert (
        pytest.approx(event_mrglv1_router.amount1, rel=1e-2, abs=1) == amount1_migrated
    )

    # compare with token amounts sent
    assert (
        event_mrglv1_router.amount0
        == mrglv1_token0.balanceOf(mrglv1_pool_initialized_with_liquidity.address)
        - balance0_mrglv1_pool
    )
    assert (
        event_mrglv1_router.amount1
        == mrglv1_token1.balanceOf(mrglv1_pool_initialized_with_liquidity.address)
        - balance1_mrglv1_pool
    )

    assert (
        pytest.approx(amount0_refunded, rel=1e-2, abs=1)
        == mrglv1_token0.balanceOf(sender.address) - balance0_sender
    )
    assert (
        pytest.approx(amount1_refunded, rel=1e-2, abs=1)
        == mrglv1_token1.balanceOf(sender.address) - balance1_sender
    )


@pytest.mark.integration
def test_migrator_migrate_with_univ3__reverts_when_unauthorized(
    mrglv1_migrator,
    mrglv1_router,
    univ3_manager,
    univ3_pool,
    mrglv1_pool_initialized_with_liquidity,
    mrglv1_token0,
    mrglv1_token1,
    sender,
    alice,
    bob,
    chain,
    mint_univ3_lp_position,
):
    tick_spacing = univ3_pool.tickSpacing()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()

    tick_upper = MAX_TICK - (MAX_TICK % tick_spacing)
    tick_lower = -tick_upper

    univ3_lp_token_id = mint_univ3_lp_position(tick_lower, tick_upper)
    univ3_lp_position = univ3_manager.positions(univ3_lp_token_id)

    # approve v1 migrator to operate with univ3 manager
    univ3_manager.approve(mrglv1_migrator.address, univ3_lp_token_id, sender=sender)

    # check bob can't frontrun and spend for himself
    percentage_to_migrate = 100
    deadline = chain.pending_timestamp + 3600
    refund_as_eth = False
    params = (
        univ3_lp_token_id,
        univ3_lp_position.liquidity,  # liquidityToRemove
        0,  # amount{0,1}MinToRemove
        0,
        percentage_to_migrate,
        0,  # amount{0,1}MinToMigrate
        0,
        maintenance,
        bob.address,
        deadline,
        refund_as_eth,
    )
    with reverts(mrglv1_migrator.Unauthorized):
        mrglv1_migrator.migrate(params, sender=bob)
