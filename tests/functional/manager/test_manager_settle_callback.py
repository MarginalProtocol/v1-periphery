from ape import reverts

from eth_abi import encode


def test_manager_settle_callback__reverts_when_not_pool(
    manager, sender, alice, spot_reserve0, spot_reserve1, token0, token1
):
    amount0 = spot_reserve0 * 1 // 10000
    amount1 = spot_reserve1 * 1 // 10000

    payer = sender.address
    maintenance = 250000
    data = encode(
        ["(address,address,uint24)", "address"],
        [(token0.address, token1.address, maintenance), payer],
    )

    # alice tries to steal from sender whose approved manager to spend
    with reverts(manager.PoolNotSender):
        manager.marginalV1SettleCallback(amount0, amount1, data, sender=alice)


def test_manager_settle_callback__reverts_when_size_less_than_min(
    manager, sender, alice, token0, token1
):
    amount0 = 0
    amount1 = 0

    payer = sender.address
    maintenance = 250000
    data = encode(
        ["(address,address,uint24)", "address"],
        [(token0.address, token1.address, maintenance), payer],
    )
    with reverts(manager.SizeLessThanMin, size=0):
        manager.marginalV1SettleCallback(amount0, amount1, data, sender=alice)
