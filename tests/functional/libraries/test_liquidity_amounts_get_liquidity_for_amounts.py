import pytest


def test_liquidity_amounts_get_liquidity_for_amounts__returns_min_of_liquidities(
    liquidity_amounts_lib,
):
    amount0 = 125040609
    amount1 = 71699650467468027
    sqrt_price_x96 = 1897197579566573828015003434745856

    liquidity0 = liquidity_amounts_lib.getLiquidityForAmount0(sqrt_price_x96, amount0)
    liquidity1 = liquidity_amounts_lib.getLiquidityForAmount1(sqrt_price_x96, amount1)
    liquidity = liquidity0 if liquidity0 < liquidity1 else liquidity1

    assert (
        liquidity_amounts_lib.getLiquidityForAmounts(sqrt_price_x96, amount0, amount1)
        == liquidity
    )


def test_liquidity_amounts_get_liquidity_for_amounts__returns_approx_liquidity_desired(
    liquidity_amounts_lib, liquidity_math_lib
):
    state_liquidity = 29942224366269117
    state_sqrt_price_x96 = 1897197579566573828015003434745856

    liquidity_delta_desired = (state_liquidity * 5) // 100  # 5% more liquidity added
    amount0_desired, amount1_desired = liquidity_math_lib.toAmounts(
        liquidity_delta_desired, state_sqrt_price_x96
    )

    liquidity_delta = liquidity_amounts_lib.getLiquidityForAmounts(
        state_sqrt_price_x96, amount0_desired, amount1_desired
    )
    amount0, amount1 = liquidity_math_lib.toAmounts(
        liquidity_delta, state_sqrt_price_x96
    )

    assert pytest.approx(liquidity_delta, rel=1e-11) == liquidity_delta_desired
    assert pytest.approx(amount0, rel=1e-11) == amount0_desired
    assert pytest.approx(amount1, rel=1e-11) == amount1_desired
