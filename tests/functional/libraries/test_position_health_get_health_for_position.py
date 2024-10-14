import pytest

from utils.constants import MAINTENANCE_UNIT
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.mark.parametrize("zero_for_one", [True, False])
def test_position_health_get_health_for_position___returns_health_factor(
    position_health_lib, zero_for_one
):
    liquidity = 29942224366269117
    sqrt_price_x96 = 1897197579566573828015003434745856
    maintenance = 250000

    reserve0, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    reserve = reserve0 if not zero_for_one else reserve1
    size = reserve * 1 // 100
    margin = (size * maintenance * 125) // (MAINTENANCE_UNIT * 100)
    total_size = size + margin

    debt = (
        (size * sqrt_price_x96**2) // (1 << 192)
        if not zero_for_one
        else (size * (1 << 192)) // (sqrt_price_x96**2)
    )
    debt = int(1.01 * debt)  # add in some slippage on the debt

    debt_adjusted = (debt * (1e6 + maintenance)) // 1e6
    debt_adjusted_in_margin = (
        (debt_adjusted * (1 << 192)) // (sqrt_price_x96**2)
        if not zero_for_one
        else (debt_adjusted * (sqrt_price_x96**2)) // (1 << 192)
    )

    health = (total_size * 1e18) // debt_adjusted_in_margin  # mul by 1e18
    result = position_health_lib.getHealthForPosition(
        zero_for_one,
        size,
        debt,
        margin,
        maintenance,
        sqrt_price_x96,
    )
    assert pytest.approx(result, rel=1e-6) == health
