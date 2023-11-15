from ape import reverts


def test_pool_address_get_address(pool_address_lib, pool, factory):
    key = (pool.token0(), pool.token1(), pool.maintenance(), pool.oracle())
    assert pool_address_lib.getAddress(factory.address, key) == pool.address


def test_pool_address_get_address__reverts_when_pool_not_exists(
    pool_address_lib, pool, factory
):
    key = (pool.token1(), pool.token0(), pool.maintenance(), pool.token1())
    with reverts(pool_address_lib.PoolInactive):
        pool_address_lib.getAddress(factory.address, key)
