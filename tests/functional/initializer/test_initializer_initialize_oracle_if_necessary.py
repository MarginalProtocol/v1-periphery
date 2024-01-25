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


def test_initializer_initialize_oracle_if_necessary__increases_oracle_cardinality(
    initializer, factory, pool, mock_univ3_pool_oracle_adjusted, sender, token0, token1
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        token0.address,
        token1.address,
        univ3_fee,
        obs_cardinality_min,
    )
    initializer.initializeOracleIfNecessary(params, sender=sender)

    result = mock_univ3_pool_oracle_adjusted.slot0()
    assert result.observationCardinalityNext == obs_cardinality_min


def test_initializer_initializes_oracle_if_necessary__passes_when_oracle_cardinality_greater_than_min(
    initializer, factory, pool, mock_univ3_pool_oracle_adjusted, sender, token0, token1
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        token0.address,
        token1.address,
        univ3_fee,
        obs_cardinality_min,
    )
    initializer.initializeOracleIfNecessary(
        params, sender=sender
    )  # increase cardinality to equal to min

    result = mock_univ3_pool_oracle_adjusted.slot0()
    assert result.observationCardinalityNext == obs_cardinality_min

    # now try again and check we pass
    params = (
        token0.address,
        token1.address,
        univ3_fee,
        obs_cardinality_min + 1,
    )
    initializer.initializeOracleIfNecessary(params, sender=sender)

    result = mock_univ3_pool_oracle_adjusted.slot0()
    assert result.observationCardinalityNext == obs_cardinality_min


def test_initializer_initialize_oracle_if_necessary__reverts_when_invalid_oracle(
    initializer,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    rando_token_a_address,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        rando_token_a_address,
        token1.address,
        univ3_fee,
        obs_cardinality_min,
    )
    with reverts(initializer.InvalidOracle):
        initializer.initializeOracleIfNecessary(params, sender=sender)


def test_initializer_initialize_oracle_if_necessary__reverts_when_token1_less_than_token0(
    initializer,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        token1.address,
        token0.address,
        univ3_fee,
        obs_cardinality_min,
    )
    with reverts():
        initializer.initializeOracleIfNecessary(params, sender=sender)


def test_initializer_initialize_oracle_if_necessary__reverts_when_oracle_cardinality_greater_than_next(
    initializer,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    slot0 = mock_univ3_pool_oracle_adjusted.slot0()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        token1.address,
        token0.address,
        univ3_fee,
        slot0.observationCardinalityNext - 1,
    )
    with reverts():
        initializer.initializeOracleIfNecessary(params, sender=sender)


def test_initializer_initialize_oracle_if_necessary__reverts_when_cardinality_next_less_than_min(
    initializer,
    factory,
    pool,
    mock_univ3_pool_oracle_adjusted,
    token0,
    token1,
    sender,
):
    obs_cardinality_min = factory.observationCardinalityMinimum()
    univ3_fee = mock_univ3_pool_oracle_adjusted.fee()
    params = (
        token1.address,
        token0.address,
        univ3_fee,
        obs_cardinality_min - 1,
    )
    with reverts():
        initializer.initializeOracleIfNecessary(params, sender=sender)
