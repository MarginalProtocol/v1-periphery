import pytest

from ape import reverts


def test_callback_validation_verify_uniswap_v3_callback_with_pool_key__returns_pool(
    callback_validation_lib, pool, mock_univ3_pool, factory
):
    factory_address = factory.address
    pool_key = (pool.token0(), pool.token1(), pool.maintenance(), pool.oracle())

    result = callback_validation_lib.verifyUniswapV3Callback(
        factory_address, pool_key, sender=mock_univ3_pool
    )
    assert result == mock_univ3_pool.address


@pytest.mark.parametrize("sorted_tokens", [True, False])
def test_callback_validation_verify_uniswap_v3_callback_with_pool_key__reverts_when_oracle_not_sender(
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
        callback_validation_lib.verifyUniswapV3Callback(factory_address, pool_key)
