import pytest

from ape.utils import ZERO_ADDRESS  # TODO: remove when implement descriptor

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture(scope="module")
def assert_mainnet_fork(networks):
    assert (
        networks.active_provider.network.name == "mainnet-fork"
    ), "network not set to mainnet-fork"


@pytest.fixture(scope="module")
def whale(assert_mainnet_fork, accounts):
    return accounts["0x8EB8a3b98659Cce290402893d0123abb75E3ab28"]  # avalanche bridge


@pytest.fixture(scope="module")
def sender(accounts):
    return accounts[3]


@pytest.fixture(scope="module")
def WETH9(assert_mainnet_fork, Contract):
    return Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture(scope="module")
def USDC(assert_mainnet_fork, Contract):
    return Contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")


@pytest.fixture(scope="module")
def univ3_factory(assert_mainnet_fork, univ3_factory_address, Contract):
    return Contract(univ3_factory_address)


@pytest.fixture(scope="module")
def univ3_pool(assert_mainnet_fork, Contract):
    return Contract("0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8")


@pytest.fixture(scope="module")
def univ3_manager(assert_mainnet_fork, Contract):
    return Contract("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")


@pytest.fixture(scope="module")
def univ3_static_quoter(assert_mainnet_fork, Contract):
    return Contract("0xc80f61d1bdAbD8f5285117e1558fDDf8C64870FE")


@pytest.fixture(scope="module")
def mrglv1_factory(project, accounts, univ3_factory):
    deployer = project.MarginalV1PoolDeployer.deploy(sender=accounts[0])
    obs_cardinality_min = (
        300  # @dev: too low for actual deployment, but needed to accomodate all tests
    )
    return project.MarginalV1Factory.deploy(
        deployer.address, univ3_factory.address, obs_cardinality_min, sender=accounts[0]
    )


# TODO: descriptor


@pytest.fixture(scope="module")
def mrglv1_manager(project, accounts, mrglv1_factory, WETH9):
    # TODO: replace zero address with descriptor
    return project.NonfungiblePositionManager.deploy(
        mrglv1_factory.address, WETH9.address, ZERO_ADDRESS, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def mrglv1_router(project, accounts, mrglv1_factory, WETH9):
    return project.Router.deploy(
        mrglv1_factory.address, WETH9.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def mrglv1_quoter(
    project, accounts, mrglv1_factory, WETH9, mrglv1_manager, univ3_static_quoter
):
    return project.Quoter.deploy(
        mrglv1_factory.address,
        WETH9.address,
        mrglv1_manager.address,
        univ3_static_quoter.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def mrglv1_initializer(project, accounts, mrglv1_factory, WETH9):
    return project.PoolInitializer.deploy(
        mrglv1_factory.address, WETH9.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def mrglv1_arbitrageur(project, accounts, mrglv1_factory, WETH9):
    return project.PairArbitrageur.deploy(
        mrglv1_factory.address, WETH9.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def mrglv1_migrator(
    project, accounts, mrglv1_factory, WETH9, mrglv1_router, univ3_manager
):
    return project.V1Migrator.deploy(
        mrglv1_factory.address,
        WETH9.address,
        mrglv1_router.address,
        univ3_manager.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def create_mrglv1_pool(project, accounts, mrglv1_factory, univ3_pool):
    def create_pool(token_a, token_b, maintenance, univ3_fee):
        tx = mrglv1_factory.createPool(
            token_a, token_b, maintenance, univ3_fee, sender=accounts[0]
        )
        pool_address = tx.decode_logs(mrglv1_factory.PoolCreated)[0].pool
        return project.MarginalV1Pool.at(pool_address)

    yield create_pool


@pytest.fixture(scope="module")
def mrglv1_pool(create_mrglv1_pool, univ3_pool):
    maintenance = 250000
    return create_mrglv1_pool(
        univ3_pool.token0(), univ3_pool.token1(), maintenance, univ3_pool.fee()
    )


@pytest.fixture(scope="module")
def mrglv1_token0(
    mrglv1_pool,
    univ3_pool,
    WETH9,
    USDC,
    sender,
    callee,
    mrglv1_manager,
    mrglv1_router,
    mrglv1_initializer,
    univ3_manager,
    whale,
):
    liquidity = univ3_pool.liquidity()
    sqrt_price_x96 = univ3_pool.slot0().sqrtPriceX96
    reserve0, _ = calc_amounts_from_liquidity_sqrt_price_x96(liquidity, sqrt_price_x96)

    token0 = USDC
    amount0 = reserve0 * 10 // 100  # 10% of spot reserves
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(mrglv1_manager.address, 2**256 - 1, sender=sender)
    token0.approve(mrglv1_router.address, 2**256 - 1, sender=sender)
    token0.approve(mrglv1_initializer.address, 2**256 - 1, sender=sender)
    token0.approve(univ3_manager.address, 2**256 - 1, sender=sender)
    token0.transfer(sender.address, amount0, sender=whale)
    return token0


@pytest.fixture(scope="module")
def mrglv1_token1(
    mrglv1_pool,
    univ3_pool,
    WETH9,
    USDC,
    sender,
    callee,
    mrglv1_manager,
    mrglv1_router,
    mrglv1_initializer,
    univ3_manager,
    whale,
):
    liquidity = univ3_pool.liquidity()
    sqrt_price_x96 = univ3_pool.slot0().sqrtPriceX96
    _, reserve1 = calc_amounts_from_liquidity_sqrt_price_x96(liquidity, sqrt_price_x96)

    token1 = WETH9
    amount1 = reserve1 * 10 // 100  # 10% of spot reserves
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(mrglv1_manager.address, 2**256 - 1, sender=sender)
    token1.approve(mrglv1_router.address, 2**256 - 1, sender=sender)
    token1.approve(mrglv1_initializer.address, 2**256 - 1, sender=sender)
    token1.approve(univ3_manager.address, 2**256 - 1, sender=sender)
    token1.transfer(sender.address, amount1, sender=whale)
    return token1


@pytest.fixture(scope="module")
def mrglv1_pool_initialized_with_liquidity(
    mrglv1_pool,
    univ3_pool,
    callee,
    mrglv1_token0,
    mrglv1_token1,
    mrglv1_router,
    swap_math_lib,
    sender,
):
    spot_liquidity = univ3_pool.liquidity()
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves

    callee.mint(mrglv1_pool.address, sender.address, liquidity_delta, sender=sender)

    # swap to current univ3 slot0 price (roughly)
    state = mrglv1_pool.state()
    slot0 = univ3_pool.slot0()
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, slot0.sqrtPriceX96
    )
    zero_for_one = amount0 > 0
    amount_specified = amount0 if zero_for_one else amount1
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
    callee.swap(
        mrglv1_pool.address,
        sender.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    mrglv1_pool.approve(mrglv1_pool.address, 2**256 - 1, sender=sender)
    mrglv1_pool.approve(mrglv1_router.address, 2**256 - 1, sender=sender)
    return mrglv1_pool
