from ape import reverts

from eth_abi import encode


def test_router_mint_callback__reverts_when_not_pool(
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

    payer = sender.address
    maintenance = 250000
    data = encode(
        ["(address,address,uint24)", "address"],
        [(token0.address, token1.address, maintenance), payer],
    )

    # alice tries to steal from sender whose approved router to spend
    with reverts(router.PoolNotSender):
        router.marginalV1MintCallback(amount0, amount1, data, sender=alice)
