import pytest

from ape import reverts


def test_callback_validation_verify_callback_with_pool_key__returns_pool(
    callback_validation_lib, pool, factory
):
    factory_address = factory.address
    pool_key = (pool.token0(), pool.token1(), pool.maintenance(), pool.oracle())

    result = callback_validation_lib.verifyCallback(
        factory_address, pool_key, sender=pool
    )
    assert result == pool.address


@pytest.mark.parametrize("sorted_tokens", [True, False])
def test_callback_validation_verify_callback_with_pool_key__reverts_when_pool_not_sender(
    callback_validation_lib, pool, factory, sorted_tokens
):
    factory_address = factory.address
    pool_key = (
        pool.token0() if sorted_tokens else pool.token1(),
        pool.token1() if sorted_tokens else pool.token0(),
        pool.maintenance(),
        pool.oracle(),
    )

    with reverts(callback_validation_lib.PoolNotSender):
        callback_validation_lib.verifyCallback(factory_address, pool_key)


@pytest.mark.parametrize("sorted_tokens", [True, False])
def test_callback_validation_verify_callback_without_pool_key__returns_pool(
    callback_validation_lib, pool, factory, sorted_tokens
):
    factory_address = factory.address
    token_a = pool.token0() if sorted_tokens else pool.token1()
    token_b = pool.token1() if sorted_tokens else pool.token0()
    maintenance = pool.maintenance()
    oracle = pool.oracle()

    result = callback_validation_lib.verifyCallback(
        factory_address,
        token_a,
        token_b,
        maintenance,
        oracle,
        sender=pool,
    )
    assert result == pool.address


@pytest.mark.parametrize("sorted_tokens", [True, False])
def test_callback_validation_verify_callback_without_pool_key__reverts_when_pool_not_sender(
    callback_validation_lib, pool, factory, sorted_tokens
):
    factory_address = factory.address
    token_a = pool.token0() if sorted_tokens else pool.token1()
    token_b = pool.token1() if sorted_tokens else pool.token0()
    maintenance = pool.maintenance()
    oracle = pool.oracle()

    with reverts(callback_validation_lib.PoolNotSender):
        callback_validation_lib.verifyCallback(
            factory_address,
            token_a,
            token_b,
            maintenance,
            oracle,
        )
