import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity, chain, position_lib, manager, sender
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


@pytest.fixture
def mint_position_with_WETH9(
    pool_with_WETH9_initialized_with_liquidity, chain, position_lib, manager, sender
):
    def mint(zero_for_one: bool) -> int:
        state = pool_with_WETH9_initialized_with_liquidity.state()
        maintenance = pool_with_WETH9_initialized_with_liquidity.maintenance()
        oracle = pool_with_WETH9_initialized_with_liquidity.oracle()

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
            pool_with_WETH9_initialized_with_liquidity.token0(),
            pool_with_WETH9_initialized_with_liquidity.token1(),
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

        premium = pool_with_WETH9_initialized_with_liquidity.rewardPremium()
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
def test_manager_lock__adjusts_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    mock_univ3_pool,
    oracle_sqrt_price_initial_x96,
    position_lib,
    position_health_lib,
    mint_position,
):
    token_id = mint_position(zero_for_one)
    maintenance = pool_initialized_with_liquidity.maintenance()

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )
    manager.lock(lock_params, sender=sender)

    position.margin += margin_in
    margin_min = position_lib.marginMinimum(position, maintenance)
    rewards = position.rewards
    health = position_health_lib.getHealthForPosition(
        zero_for_one,
        position.size,
        position.debt0 if zero_for_one else position.debt1,
        position.margin,
        maintenance,
        oracle_sqrt_price_initial_x96,
    )

    assert pool_initialized_with_liquidity.positions(key) == position
    assert manager.positions(token_id) == (
        pool_initialized_with_liquidity.address,
        position_id,
        zero_for_one,
        position.size,
        position.debt0 if zero_for_one else position.debt1,
        position.margin,
        margin_min,  # oracle tick == pool tick in conftest.py
        position.liquidated,
        True,  # should be safe
        rewards,
        health,
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_lock__transfers_funds(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    token0,
    token1,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    token = token0 if not zero_for_one else token1
    balance_sender = token.balanceOf(sender.address)
    balance_pool = token.balanceOf(pool_initialized_with_liquidity.address)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )
    manager.lock(lock_params, sender=sender)

    assert token.balanceOf(sender.address) == balance_sender - margin_in
    assert (
        token.balanceOf(pool_initialized_with_liquidity.address)
        == balance_pool + margin_in
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_lock__emits_lock(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )
    tx = manager.lock(lock_params, sender=sender)

    # refresh position state
    position = pool_initialized_with_liquidity.positions(key)

    events = tx.decode_logs(manager.Lock)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == token_id
    assert event.sender == sender.address
    assert event.marginAfter == position.margin
    # assert tx.return_value == position.margin  # TODO: fix


def test_manager_lock__deposits_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    manager,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    mint_position_with_WETH9,
):
    zero_for_one = (
        token1_with_WETH9.address == WETH9.address
    )  # margin in token1 if true
    token_id = mint_position_with_WETH9(zero_for_one)

    position_id = pool_with_WETH9_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_with_WETH9_initialized_with_liquidity.positions(key)

    token = token0_with_WETH9 if not zero_for_one else token1_with_WETH9
    assert token.address == WETH9.address

    # set WETH9 allowance to zero to ensure all payment in ETH
    WETH9.approve(manager.address, 0, sender=sender)

    balancee_sender = sender.balance
    balancee_WETH9 = WETH9.balance

    balance_sender = token.balanceOf(sender.address)
    balance_pool = token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_with_WETH9_initialized_with_liquidity.token0(),
        pool_with_WETH9_initialized_with_liquidity.token1(),
        pool_with_WETH9_initialized_with_liquidity.maintenance(),
        pool_with_WETH9_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )
    tx = manager.lock(lock_params, sender=sender, value=margin_in)

    # WETH9 balance changes
    assert token.balanceOf(sender.address) == balance_sender  # shouldn't change
    assert (
        token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance_pool + margin_in
    )

    # native (gas) token balance changes
    assert sender.balance == balancee_sender - margin_in - tx.gas_used * tx.gas_price
    assert WETH9.balance == balancee_WETH9 + margin_in


def test_manager_lock__pays_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    manager,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    mint_position_with_WETH9,
):
    zero_for_one = (
        token1_with_WETH9.address == WETH9.address
    )  # margin in token1 if true
    token_id = mint_position_with_WETH9(zero_for_one)

    position_id = pool_with_WETH9_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_with_WETH9_initialized_with_liquidity.positions(key)

    token = token0_with_WETH9 if not zero_for_one else token1_with_WETH9
    assert token.address == WETH9.address

    balancee_sender = sender.balance
    balancee_WETH9 = WETH9.balance

    balance_sender = token.balanceOf(sender.address)
    balance_pool = token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_with_WETH9_initialized_with_liquidity.token0(),
        pool_with_WETH9_initialized_with_liquidity.token1(),
        pool_with_WETH9_initialized_with_liquidity.maintenance(),
        pool_with_WETH9_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )
    tx = manager.lock(lock_params, sender=sender)

    # WETH9 balance changes
    assert token.balanceOf(sender.address) == balance_sender - margin_in
    assert (
        token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance_pool + margin_in
    )

    # native (gas) token balance changes
    assert (
        sender.balance == balancee_sender - tx.gas_used * tx.gas_price
    )  # shouldn't change less gas fees
    assert WETH9.balance == balancee_WETH9  # shouldn't change


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_lock__reverts_when_not_owner(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )

    with reverts(manager.Unauthorized):
        manager.lock(lock_params, sender=alice)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_lock__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp - 1
    margin_in = (position.margin * 25) // 100
    lock_params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.maintenance(),
        pool_initialized_with_liquidity.oracle(),
        token_id,
        margin_in,
        deadline,
    )

    with reverts("Transaction too old"):
        manager.lock(lock_params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_lock__reverts_when_invalid_pool_key(
    pool_initialized_with_liquidity,
    rando_pool,
    manager,
    zero_for_one,
    sender,
    chain,
    mint_position,
):
    token_id = mint_position(zero_for_one)

    position_id = pool_initialized_with_liquidity.state().totalPositions - 1
    key = get_position_key(manager.address, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    deadline = chain.pending_timestamp + 3600
    margin_in = (position.margin * 25) // 100
    lock_params = (
        rando_pool.token0(),
        rando_pool.token1(),
        rando_pool.maintenance(),
        rando_pool.oracle(),
        token_id,
        margin_in,
        deadline,
    )

    with reverts(manager.InvalidPoolKey):
        manager.lock(lock_params, sender=sender)
