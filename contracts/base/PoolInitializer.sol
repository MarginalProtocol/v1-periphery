// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity =0.8.15;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {PoolAddress as UniswapV3PoolAddress} from "@uniswap/v3-periphery/contracts/libraries/PoolAddress.sol";

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {IPoolInitializer} from "../interfaces/IPoolInitializer.sol";

/// @title Creates and initializes V1 Pools
/// @dev Fork of Uniswap V3 periphery PoolInitializer.sol, adapted to Marginal V1
abstract contract PoolInitializer is IPoolInitializer, PeripheryImmutableState {
    // TODO: test
    /// @inheritdoc IPoolInitializer
    function createAndInitializePoolIfNecessary(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 uniswapV3Fee,
        uint160 sqrtPriceX96
    ) external payable override returns (address pool) {
        require(token0 < token1);
        address oracle = UniswapV3PoolAddress.computeAddress(
            uniswapV3Factory,
            UniswapV3PoolAddress.PoolKey({
                token0: token0,
                token1: token1,
                fee: uniswapV3Fee
            })
        );
        pool = IMarginalV1Factory(factory).getPool(
            token0,
            token1,
            maintenance,
            oracle
        );

        if (pool == address(0)) {
            pool = IMarginalV1Factory(factory).createPool(
                token0,
                token1,
                maintenance,
                uniswapV3Fee
            );
            IMarginalV1Pool(pool).initialize(sqrtPriceX96);
        } else {
            (, uint160 sqrtPriceX96Existing, , , , , , ) = IMarginalV1Pool(pool)
                .state();
            if (sqrtPriceX96Existing == 0) {
                IMarginalV1Pool(pool).initialize(sqrtPriceX96);
            }
        }
    }
}
