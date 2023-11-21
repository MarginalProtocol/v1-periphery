import pytest

from ape import reverts


@pytest.fixture
def mock_univ3_pool_oracle_adjusted(mock_univ3_pool, factory, sender):
    # set mock oracle so obs cardinality < obs cardinality minu
    obs_cardinality_min = factory.observationCardinalityMinimum()
    slot0 = mock_univ3_pool.slot0()
    slot0.observationCardinality = obs_cardinality_min - 1
    slot0.observationCardinalityNext = obs_cardinality_min - 1
    mock_univ3_pool.setSlot0(slot0, sender=sender)
    return mock_univ3_pool


def test_router_initialize_oracle_if_necessary__increases_oracle_cardinality(
    router, factory, pool, mock_univ3_pool_oracle_adjusted, sender, token0, token1
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    router.initializeOracleIfNecessary(
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        obs_cardinality_min,
        sender=sender,
    )

    result = mock_univ3_pool_oracle_adjusted.slot0()
    assert result.observationCardinalityNext == obs_cardinality_min


def test_router_initializes_oracle_if_necessary__passes_when_oracle_cardinality_greater_than_min(
    router, factory, pool, mock_univ3_pool, sender, token0, token1
):
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool.fee()
    slot0 = mock_univ3_pool.slot0()
    router.initializeOracleIfNecessary(
        token0.address,
        token1.address,
        maintenance,
        univ3_fee,
        slot0.observationCardinalityNext + 1,
        sender=sender,
    )

    result = mock_univ3_pool.slot0()
    assert result.observationCardinalityNext == slot0.observationCardinalityNext


def test_router_initialize_oracle_if_necessary__reverts_when_invalid_oracle(
    router,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    rando_token_a_address,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    with reverts(router.InvalidOracle):
        router.initializeOracleIfNecessary(
            rando_token_a_address,
            token1.address,
            maintenance,
            univ3_fee,
            obs_cardinality_min,
            sender=sender,
        )


def test_router_initialize_oracle_if_necessary__reverts_when_token1_less_than_token0(
    router,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    with reverts():
        router.initializeOracleIfNecessary(
            token1.address,
            token0.address,
            maintenance,
            univ3_fee,
            obs_cardinality_min,
            sender=sender,
        )


def test_router_initialize_oracle_if_necessary__reverts_when_oracle_cardinality_greater_than_next(
    router,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    slot0 = mock_univ3_pool_oracle_adjusted.slot0()
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    with reverts():
        router.initializeOracleIfNecessary(
            token1.address,
            token0.address,
            maintenance,
            univ3_fee,
            slot0.observationCardinalityNext - 1,
            sender=sender,
        )


def test_router_initialize_oracle_if_necessary__reverts_when_cardinality_next_less_than_min(
    router,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    maintenance = pool.maintenance()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    with reverts():
        router.initializeOracleIfNecessary(
            token1.address,
            token0.address,
            maintenance,
            univ3_fee,
            obs_cardinality_min - 1,
            sender=sender,
        )
