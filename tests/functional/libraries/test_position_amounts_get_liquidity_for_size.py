import pytest

from ape import reverts

from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_position_amounts_get_liquidity_for_size__returns_liquidity_delta(
    position_amounts_lib, zero_for_one
):
    liquidity = 29942224366269117
    sqrt_price_x96 = 1897197579566573828015003434745856
    maintenance = 250000

    reserve0, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    reserve = reserve0 if not zero_for_one else reserve1
    size = reserve * 1 // 100

    prod = (reserve - size) ** 2 // reserve
    denom = reserve - (prod * 1e6) // (1e6 + maintenance)
    liquidity_delta = int((liquidity * size) // denom)

    assert (
        pytest.approx(
            position_amounts_lib.getLiquidityForSize(
                liquidity, sqrt_price_x96, maintenance, zero_for_one, size
            ),
            rel=1e-15,
        )
        == liquidity_delta
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_position_amounts_get_liquidity_for_size__returns_size_from_position_lib(
    position_amounts_lib, position_lib, sqrt_price_math_lib, zero_for_one
):
    liquidity = 29942224366269117
    sqrt_price_x96 = 1897197579566573828015003434745856
    maintenance = 250000

    reserve0, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    reserve = reserve0 if not zero_for_one else reserve1
    size = reserve * 1 // 100

    liquidity_delta = position_amounts_lib.getLiquidityForSize(
        liquidity, sqrt_price_x96, maintenance, zero_for_one, size
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert (
        pytest.approx(
            position_lib.size(
                liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
            ),
            rel=1e-15,
        )
        == size
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_position_amounts_get_liquidity_for_size__reverts_when_size_greater_than_reserve(
    position_amounts_lib, zero_for_one
):
    liquidity = 29942224366269117
    sqrt_price_x96 = 1897197579566573828015003434745856
    maintenance = 250000

    reserve0, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    reserve = reserve0 if not zero_for_one else reserve1
    size = reserve

    with reverts(position_amounts_lib.SizeGreaterThanReserve):
        position_amounts_lib.getLiquidityForSize(
            liquidity, sqrt_price_x96, maintenance, zero_for_one, size
        )
