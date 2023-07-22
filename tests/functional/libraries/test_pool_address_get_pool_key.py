def test_pool_address_get_pool_key__with_a_less_than_b(pool_address_lib, pool):
    token_a = pool.token0()
    token_b = pool.token1()
    maintenance = pool.maintenance()
    oracle = pool.oracle()
    assert pool_address_lib.getPoolKey(token_a, token_b, maintenance, oracle) == (
        token_a,
        token_b,
        maintenance,
        oracle,
    )


def test_pool_address_get_pool_key__with_a_greater_than_b(pool_address_lib, pool):
    token_a = pool.token1()
    token_b = pool.token0()
    maintenance = pool.maintenance()
    oracle = pool.oracle()
    assert pool_address_lib.getPoolKey(token_a, token_b, maintenance, oracle) == (
        token_b,
        token_a,
        maintenance,
        oracle,
    )
