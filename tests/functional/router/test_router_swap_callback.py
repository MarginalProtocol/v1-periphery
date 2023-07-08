from ape import reverts

from eth_abi import encode
from eth_abi.packed import encode_packed


def test_router_swap_callback__reverts_when_not_pool_with_zero_for_one(
    router,
    sender,
    alice,
    spot_reserve0,
    spot_reserve1,
    token0,
    token1,
):
    amount0 = spot_reserve0 // 10000
    amount1 = spot_reserve1 // 10000

    token_in = token0.address
    token_out = token1.address

    amount0_delta = amount0
    amount1_delta = -amount1

    payer = sender.address
    maintenance = 250000

    path = encode_packed(
        ["address", "uint24", "address"], [token_in, maintenance, token_out]
    )
    data = encode(["(bytes,address)"], [(path, payer)])

    # alice tries to steal from sender whose approved router to spend
    with reverts(router.PoolNotSender):
        router.marginalV1SwapCallback(amount0_delta, amount1_delta, data, sender=alice)


def test_router_swap_callback__reverts_when_not_pool_with_one_for_zero(
    router,
    sender,
    alice,
    spot_reserve0,
    spot_reserve1,
    token0,
    token1,
):
    amount0 = spot_reserve0 // 10000
    amount1 = spot_reserve1 // 10000

    token_in = token1.address
    token_out = token0.address

    amount0_delta = -amount0
    amount1_delta = amount1

    payer = sender.address
    maintenance = 250000

    path = encode_packed(
        ["address", "uint24", "address"], [token_in, maintenance, token_out]
    )
    data = encode(["(bytes,address)"], [(path, payer)])

    # alice tries to steal from sender whose approved router to spend
    with reverts(router.PoolNotSender):
        router.marginalV1SwapCallback(amount0_delta, amount1_delta, data, sender=alice)
