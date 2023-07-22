from ape import reverts


def test_pool_address_compute_address(pool_address_lib, pool, factory):
    deployer_address = factory.marginalV1Deployer()
    key = (pool.token0(), pool.token1(), pool.maintenance(), pool.oracle())
    assert (
        pool_address_lib.computeAddress(deployer_address, factory.address, key)
        == pool.address
    )


def test_pool_address_reverts_when_token0_less_than_token1(
    pool_address_lib, pool, factory
):
    deployer_address = factory.marginalV1Deployer()
    key = (pool.token1(), pool.token0(), pool.maintenance(), pool.oracle())
    with reverts():
        pool_address_lib.computeAddress(deployer_address, factory.address, key)
