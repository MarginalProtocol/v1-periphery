import pytest

from eth_abi.packed import encode_packed
from hexbytes import HexBytes

from utils.constants import POP_OFFSET


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
            "address",  # token out 1 / token in 2
            "uint24",  # maintenance 2
            "address",  # oracle 2
            "address",  # token out 2
        ],
        [
            rando_token_a_address,
            250000,
            mock_univ3_pool.address,
            rando_token_b_address,
            500000,
            mock_univ3_pool.address,
            rando_token_a_address,
            1000000,
            mock_univ3_pool.address,
            rando_token_b_address,
        ],
    )


def test_path_get_first_pool__when_single_path(
    path_lib, single_path, rando_token_a_address, rando_token_b_address, mock_univ3_pool
):
    assert path_lib.getFirstPool(single_path) == single_path[:POP_OFFSET]


def test_path_get_first_pool__when_multi_path(
    path_lib, multi_path, rando_token_a_address, rando_token_b_address, mock_univ3_pool
):
    assert path_lib.getFirstPool(multi_path) == multi_path[:POP_OFFSET]
