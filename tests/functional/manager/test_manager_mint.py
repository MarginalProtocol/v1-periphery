import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FEE,
    REWARD,
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
    manager.mint(mint_params, sender=sender)

    owner = manager.address
    id = state.totalPositions
    key = get_position_key(owner, id)
    result = pool_initialized_with_liquidity.positions(key)
    assert result == position


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__mints_token(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
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
    manager.mint(mint_params, sender=sender)

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
    reward = pool_initialized_with_liquidity.reward()
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
    manager.mint(mint_params, sender=sender)

    position_id = state.totalPositions
    owner = manager.address

    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_min = position_lib.marginMinimum(position, maintenance)
    rewards = position_lib.liquidationRewards(position.size, reward)

    next_id = 1
    assert manager.positions(next_id) == (
        pool_initialized_with_liquidity.address,
        position_id,
        zero_for_one,
        position.size,
        position.debt0 if zero_for_one else position.debt1,
        position.margin,
        margin_min,
        position.liquidated,
        rewards,
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
    manager.mint(mint_params, sender=sender)

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)

    fees = position_lib.fees(position.size, FEE)
    rewards = position_lib.liquidationRewards(position.size, REWARD)
    amount_in = position.margin + rewards + fees

    assert token.balanceOf(sender.address) == balance_sender - amount_in
    assert (
        token.balanceOf(pool_initialized_with_liquidity.address)
        == balance_pool + amount_in
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__emits_mint(
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
    tx = manager.mint(mint_params, sender=sender)

    position_id = state.totalPositions
    owner = manager.address
    key = get_position_key(owner, position_id)
    position = pool_initialized_with_liquidity.positions(key)
    debt = position.debt0 if zero_for_one else position.debt1

    fees = position_lib.fees(position.size, FEE)
    rewards = position_lib.liquidationRewards(position.size, REWARD)
    amount_in = position.margin + rewards + fees

    next_id = 1
    events = tx.decode_logs(manager.Mint)
    assert len(events) == 1

    event = events[0]
    assert event.tokenId == next_id
    assert event.size == position.size
    assert event.debt == debt
    assert event.amountIn == amount_in
    # assert tx.return_value == (next_id, position.size, debt)  # TODO: fix


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_sqrt_price_limit_x96_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
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
    tx = manager.mint(mint_params, sender=sender)
    token_id = tx.decode_logs(manager.Mint)[0].tokenId
    assert token_id == 1  # token with ID 1 minted


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_debt_max_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
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
    tx = manager.mint(mint_params, sender=sender)
    token_id = tx.decode_logs(manager.Mint)[0].tokenId
    assert token_id == 1  # token with ID 1 minted


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__when_amount_in_max_is_zero(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
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
    tx = manager.mint(mint_params, sender=sender)
    token_id = tx.decode_logs(manager.Mint)[0].tokenId
    assert token_id == 1  # token with ID 1 minted


# TODO: new pool with weth9
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__deposits_weth(zero_for_one, sender):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__reverts_when_past_deadline(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    chain,
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

    with reverts("Transaction too old"):
        manager.mint(mint_params, sender=sender)


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

    with reverts(manager.SizeLessThanMin, size=position.size):
        manager.mint(mint_params, sender=sender)


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

    with reverts(manager.DebtGreaterThanMax, debt=debt):
        manager.mint(mint_params, sender=sender)


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
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    amount_in = margin + rewards + fees
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
        manager.mint(mint_params, sender=sender)
