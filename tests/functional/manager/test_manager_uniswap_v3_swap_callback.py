from ape import reverts

from eth_abi import encode


def test_manager_uniswap_v3_swap_callback__reverts_when_not_oracle(
    manager, sender, alice, spot_reserve0, spot_reserve1, token0, token1, pool
):
    amount0 = spot_reserve0 * 1 // 10000
    amount1 = spot_reserve1 * 1 // 10000

    # transfer some tokens from sender to manager
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0 = balance0_sender * 1 // 10000
    balance1 = balance1_sender * 1 // 10000

    token0.transfer(manager.address, balance0, sender=sender)
    token1.transfer(manager.address, balance1, sender=sender)
    assert token0.balanceOf(manager.address) == balance0
    assert token1.balanceOf(manager.address) == balance1

    maintenance = 250000
    oracle = pool.oracle()
    data = encode(
        ["(address,address,uint24,address)"],
        [(token0.address, token1.address, maintenance, oracle)],
    )

    # alice tries to steal from manager
    with reverts(manager.OracleNotSender):
        manager.uniswapV3SwapCallback(amount0, amount1, data, sender=alice)
