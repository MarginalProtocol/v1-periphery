import pytest

from eth_abi.packed import encode_packed
from hexbytes import HexBytes


@pytest.fixture
def single_path(
    rando_token_a_address, rando_token_b_address, mock_univ3_pool
) -> HexBytes:
    return encode_packed(
        [
            "address",  # token in
            "uint24",  # maintenance
            "address",  # oracle
            "address",  # token out
        ],
        [rando_token_a_address, 250000, mock_univ3_pool.address, rando_token_b_address],
    )


@pytest.fixture
def multi_path(
    rando_token_a_address, rando_token_b_address, mock_univ3_pool
) -> HexBytes:
    return encode_packed(
        [
            "address",  # token in 0
            "uint24",  # maintenance 0
            "address",  # oracle 0
            "address",  # token out 0 / token in 1
            "uint24",  # maintenance 1
            "address",  # oracle 1
            "address",  # token out 1
        ],
        [
            rando_token_a_address,
            250000,
            mock_univ3_pool.address,
            rando_token_b_address,
            500000,
            mock_univ3_pool.address,
            rando_token_a_address,
        ],
    )


def test_path_has_multiple_pools__when_single_path(path_lib, single_path):
    assert path_lib.hasMultiplePools(single_path) is False


def test_path_has_multiple_pools__when_multi_path(path_lib, multi_path):
    assert path_lib.hasMultiplePools(multi_path) is True
