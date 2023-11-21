from ape import project, reverts
from ape.utils import ZERO_ADDRESS


def test_router_create_and_initialize_pool_if_necessary__creates_pool_when_not_exists(
    router, factory, mock_univ3_pool, token0, token1, sqrt_price_x96_initial, sender
):
    maintenance = 1000000
    univ3_fee = mock_univ3_pool.fee()
    assert (
        factory.getPool(
            token0.address, token1.address, maintenance, mock_univ3_pool.address
        )
        == ZERO_ADDRESS
    )

    router.createAndInitializePoolIfNecessary(
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        sqrt_price_x96_initial,
        sender=sender,
    )

    pool_address = factory.getPool(
        token0.address, token1.address, maintenance, mock_univ3_pool.address
    )
    assert pool_address != ZERO_ADDRESS

    p = project.MarginalV1Pool.at(pool_address)
    state = p.state()
    assert state.initialized is True
    assert state.sqrtPriceX96 == sqrt_price_x96_initial


def test_router_create_and_initialize_pool_if_necessary__initializes_pool_when_exists(
    router, create_pool, mock_univ3_pool, token0, token1, sqrt_price_x96_initial, sender
):
    maintenance = 1000000
    univ3_fee = mock_univ3_pool.fee()
    p = create_pool(token0.address, token1.address, maintenance, univ3_fee)
    assert p.state().initialized is False

    router.createAndInitializePoolIfNecessary(
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        sqrt_price_x96_initial,
        sender=sender,
    )

    state = p.state()
    assert state.initialized is True
    assert state.sqrtPriceX96 == sqrt_price_x96_initial


def test_router_create_and_initialize_pool_if_necessary__passes_when_pool_initialized(
    router,
    pool_initialized,
    mock_univ3_pool,
    token0,
    token1,
    sqrt_price_x96_initial,
    sender,
):
    maintenance = pool_initialized.maintenance()
    univ3_fee = mock_univ3_pool.fee()
    assert pool_initialized.state().initialized is True

    router.createAndInitializePoolIfNecessary(
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        sqrt_price_x96_initial + 1,
        sender=sender,
    )

    state = pool_initialized.state()
    assert state.sqrtPriceX96 == sqrt_price_x96_initial


def test_router_create_and_initialize_pool_if_necessary__reverts_when_invalid_oracle(
    router,
    pool_initialized,
    mock_univ3_pool,
    rando_token_a_address,
    token1,
    sqrt_price_x96_initial,
    sender,
):
    maintenance = pool_initialized.maintenance()
    univ3_fee = mock_univ3_pool.fee()
    with reverts(router.InvalidOracle):
        router.createAndInitializePoolIfNecessary(
            rando_token_a_address,
            token1.address,
            maintenance,
            univ3_fee,
            sqrt_price_x96_initial,
            sender=sender,
        )


def test_router_create_and_initialize_pool_if_necessary__reverts_when_token1_less_than_token0(
    router,
    pool_initialized,
    mock_univ3_pool,
    token0,
    token1,
    sqrt_price_x96_initial,
    sender,
):
    maintenance = pool_initialized.maintenance()
    univ3_fee = mock_univ3_pool.fee()
    with reverts():
        router.createAndInitializePoolIfNecessary(
            token1.address,
            token0.address,
            maintenance,
            univ3_fee,
            sqrt_price_x96_initial,
            sender=sender,
        )
