def test_liquidity_amounts_get_liquidity_for_amount1(liquidity_amounts_lib):
    amount1 = 71699650467468027
    sqrt_price_x96 = 1897197579566573828015003434745856

    liquidity1 = (amount1 * (1 << 96)) // sqrt_price_x96
    assert (
        liquidity_amounts_lib.getLiquidityForAmount1(sqrt_price_x96, amount1)
        == liquidity1
    )
