import pytest


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__opens_position(
    pool_initialized_with_liquidity, manager, zero_for_one
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__mints_token(
    pool_initialized_with_liquidity, manager, zero_for_one
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__sets_position_ref(
    pool_initialized_with_liquidity, manager, zero_for_one
):
    pass


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__emits_mint(
    pool_initialized_with_liquidity, manager, zero_for_one
):
    pass


# TODO: new pool with weth9
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_manager_mint__deposits_weth(zero_for_one):
    pass


def test_manager_mint__reverts_when_past_deadline(
    pool_initialized_with_liquidity, manager
):
    pass
