def test_liquidity_amounts_get_liquidity_for_amount0(liquidity_amounts_lib):
    amount0 = 125040609
    sqrt_price_x96 = 1897197579566573828015003434745856

    liquidity0 = (amount0 * sqrt_price_x96) // (1 << 96)
    assert (
        liquidity_amounts_lib.getLiquidityForAmount0(sqrt_price_x96, amount0)
        == liquidity0
    )
