import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FEE,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__opens_position(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    position_amounts_lib,
    rando_univ3_observations,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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

    liquidity_delta = position_amounts_lib.getLiquidityForSize(
        state.liquidity, state.sqrtPriceX96, maintenance, zero_for_one, size
    )  # ~ 5% for 1% size

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        block_timestamp_next,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    position.margin = margin
    position.liquidityLocked = liquidity_delta

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

    manager.mint(mint_params, sender=sender, value=rewards)

    owner = manager.address
    id = state.totalPositions
    key = get_position_key(owner, id)
    result = pool_initialized_with_liquidity.positions(key)

    position.rewards = result.rewards
    assert result == position
    assert rewards >= result.rewards


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__mints_token(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    manager.mint(mint_params, sender=sender, value=rewards)

    next_id = 1  # starts at 1 for nft position manager
    assert manager.ownerOf(next_id) == sender.address
    assert manager.balanceOf(sender.address) == 1


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__sets_position_ref(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    manager.mint(mint_params, sender=sender, value=rewards)

    position_id = state.totalPositions
    owner = manager.address

    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_min = position_lib.marginMinimum(position, maintenance)

    next_id = 1
    assert manager.positions(next_id) == (
        pool_initialized_with_liquidity.address,
        position_id,
        zero_for_one,
        position.size,
        position.debt0 if zero_for_one else position.debt1,
        position.margin,
        margin_min,  # oracle tick == pool tick in conftest.py
        position.liquidated,
        True,  # should be safe
        position.rewards,
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__transfers_funds(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    token0,
    token1,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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

    token = token1 if zero_for_one else token0
    balance_sender = token.balanceOf(sender.address)
    balance_pool = token.balanceOf(pool_initialized_with_liquidity.address)

    balancee_sender = sender.balance
    balancee_pool = pool_initialized_with_liquidity.balance

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

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    fees = position_lib.fees(position.size, FEE)
    amount_in = position.margin + fees

    assert token.balanceOf(sender.address) == balance_sender - amount_in
    assert (
        token.balanceOf(pool_initialized_with_liquidity.address)
        == balance_pool + amount_in
    )

    assert (
        sender.balance
        == balancee_sender - position.rewards - tx.gas_used * tx.gas_price
    )
    assert pool_initialized_with_liquidity.balance == balancee_pool + position.rewards


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__refunds_eth(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    token0,
    token1,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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

    balancee_sender = sender.balance
    balancee_pool = pool_initialized_with_liquidity.balance

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
    value = rewards * 2

    tx = manager.mint(mint_params, sender=sender, value=value)

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    assert value > position.rewards
    assert (
        sender.balance
        == balancee_sender - position.rewards - tx.gas_used * tx.gas_price
    )
    assert pool_initialized_with_liquidity.balance == balancee_pool + position.rewards


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__emits_mint(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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
        alice.address,
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

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)
    debt = position.debt0 if zero_for_one else position.debt1
    fees = position_lib.fees(position.size, FEE)

    next_id = 1
    events = tx.decode_logs(manager.Mint)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == next_id
    assert event.sender == sender.address
    assert event.recipient == alice.address
    assert event.positionId == position_id
    assert event.size == position.size
    assert event.debt == debt
    assert event.margin == position.margin
    assert event.fees == fees
    assert event.rewards == position.rewards
    # assert tx.return_value == (next_id, position.size, debt)  # TODO: fix


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_sqrt_price_limit_x96_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = 0
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
    assert token_id == 1  # token with ID 1 minted


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_debt_max_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    debt_max = 0
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
    assert token_id == 1  # token with ID 1 minted


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_amount_in_max_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    debt_max = 2**128 - 1
    amount_in_max = 0
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
    assert token_id == 1  # token with ID 1 minted


def test_manager_mint__deposits_WETH9(
    pool_with_WETH9_initialized_with_liquidity,
    manager,
    sender,
    alice,
    chain,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    position_lib,
):
    state = pool_with_WETH9_initialized_with_liquidity.state()
    maintenance = pool_with_WETH9_initialized_with_liquidity.maintenance()
    oracle = pool_with_WETH9_initialized_with_liquidity.oracle()

    # set WETH9 allowance to zero to ensure all payment in ETH
    WETH9.approve(manager.address, 0, sender=sender)

    zero_for_one = (
        token1_with_WETH9.address == WETH9.address
    )  # margin in token1 if true for ETH in

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

    token = WETH9
    balance_sender = token.balanceOf(sender.address)
    balance_pool = token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)

    balancee_sender = sender.balance
    balancee_pool = pool_with_WETH9_initialized_with_liquidity.balance
    balancee_WETH9 = WETH9.balance

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
    fees = position_lib.fees(size, FEE)

    amounte_in = margin + fees + rewards
    value = (amounte_in * 101) // 100  # to test refunds excess ETH

    tx = manager.mint(mint_params, sender=sender, value=value)

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_with_WETH9_initialized_with_liquidity.positions(key)
    fees = position_lib.fees(position.size, FEE)

    # reset amounts in given gas likely decreased so lower rewards
    amounte_in = margin + fees + position.rewards
    value = (amounte_in * 101) // 100  # to test refunds excess ETH
    amount_in = margin + fees  # in to WETH

    # check balance changes
    assert (
        token.balanceOf(sender.address) == balance_sender
    )  # no WETH change to sender balance
    assert (
        token.balanceOf(pool_with_WETH9_initialized_with_liquidity.address)
        == balance_pool + amount_in
    )
    assert sender.balance == balancee_sender - amounte_in - tx.gas_used * tx.gas_price
    assert (
        pool_with_WETH9_initialized_with_liquidity.balance
        == balancee_pool + position.rewards
    )
    assert WETH9.balance == balancee_WETH9 + amount_in


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

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
    deadline = chain.pending_timestamp - 1

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

    with reverts("Transaction too old"):
        manager.mint(mint_params, sender=sender, value=rewards)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_size_less_than_min(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    position_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    debt_max = 2**128 - 1
    amount_in_max = 2**256 - 1
    deadline = chain.pending_timestamp + 3600

    liquidity_delta = position_amounts_lib.getLiquidityForSize(
        state.liquidity, state.sqrtPriceX96, maintenance, zero_for_one, size
    )  # ~ 5% for 1% size

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,
        0,
        0,
    )
    size_min = position.size + 1

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
    rewards *= 1000  # set much higher since tx going to revert

    with reverts(manager.SizeLessThanMin, size=position.size):
        manager.mint(mint_params, sender=sender, value=rewards)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_debt_greater_than_max(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    position_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    deadline = chain.pending_timestamp + 3600

    liquidity_delta = position_amounts_lib.getLiquidityForSize(
        state.liquidity, state.sqrtPriceX96, maintenance, zero_for_one, size
    )  # ~ 5% for 1% size

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,
        0,
        0,
    )
    debt = position.debt0 if zero_for_one else position.debt1
    debt_max = debt - 1
    amount_in_max = 2**256 - 1

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
    rewards *= 1000  # set much higher since tx going to revert

    with reverts(manager.DebtGreaterThanMax, debt=debt):
        manager.mint(mint_params, sender=sender, value=rewards)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_amount_in_greater_than_max(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    position_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    deadline = chain.pending_timestamp + 3600

    liquidity_delta = position_amounts_lib.getLiquidityForSize(
        state.liquidity, state.sqrtPriceX96, maintenance, zero_for_one, size
    )  # ~ 5% for 1% size

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,
        0,
        0,
    )
    fees = position_lib.fees(position.size, FEE)
    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )
    rewards *= 1000  # set much higher since tx going to revert

    amount_in = margin + fees
    amount_in_max = amount_in - 1
    debt_max = 2**128 - 1

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

    with reverts(manager.AmountInGreaterThanMax, amountIn=amount_in):
        manager.mint(mint_params, sender=sender, value=rewards)


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_liquidation_rewards_less_than_min(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
    position_lib,
    sqrt_price_math_lib,
    position_amounts_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    oracle = pool_initialized_with_liquidity.oracle()

    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    reserve = reserve1 if zero_for_one else reserve0

    size = reserve * 1 // 100  # 1% of reserves
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    size_min = (size * 80) // 100
    deadline = chain.pending_timestamp + 3600

    amount_in_max = 2**256 - 1
    debt_max = 2**128 - 1

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

    with reverts(manager.RewardsLessThanMin):
        manager.mint(mint_params, sender=sender)
