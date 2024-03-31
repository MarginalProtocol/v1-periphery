import pytest

from ape import reverts

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def mint_position(
    pool_initialized_with_liquidity, position_lib, chain, manager, sender
):
    def mint(zero_for_one: bool, bps_of_reserve: int) -> int:
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

        size = (reserve * bps_of_reserve) // 10000  # % of reserves in bps
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
def test_manager_token_uri__returns_base64_string(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mock_univ3_pool,
    position_lib,
    mint_position,
    token0,
    token1,
):
    token_id = mint_position(zero_for_one, 100)  # 1% of reserve (~ 12.5K A, ~ 7.2 B)
    token_uri = manager.tokenURI(token_id)
    assert len(token_uri) > 0

    data_prefix = "data:application/json;base64"
    assert token_uri[: len(data_prefix)] == data_prefix


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_token_uri__returns_base64_string_with_decimals(
    pool_initialized_with_liquidity,
    manager,
    zero_for_one,
    sender,
    alice,
    chain,
    mock_univ3_pool,
    position_lib,
    mint_position,
    token0,
    token1,
):
    token_id = mint_position(zero_for_one, 1)  # 1% of reserve (~ 125 A, ~ .07 B)
    token_uri = manager.tokenURI(token_id)
    assert len(token_uri) > 0

    data_prefix = "data:application/json;base64"
    assert token_uri[: len(data_prefix)] == data_prefix


def test_manager_token_uri__reverts_when_token_not_exists(manager):
    token_id = 1
    with reverts():
        manager.tokenURI(token_id)
