// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity ^0.8.0;

import {IUniswapV3Pool} from "@marginal/v1-core/contracts/interfaces/vendor/kodiak/IUniswapV3Pool.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PoolAddress} from "./PoolAddress.sol";

/// @notice Provides validation for callbacks from Marginal V1 Pools
/// @dev Fork of Uniswap V3 periphery CallbackValidation.sol
library CallbackValidation {
    error PoolNotSender();
    error OracleNotSender();

    /// @notice Returns the address of a valid Marginal V1 Pool
    /// @param factory The contract address of the Marginal V1 factory
    /// @param tokenA The contract address of either token0 or token1
    /// @param tokenB The contract address of the other token
    /// @param maintenance The maintenance requirements of the pool
    /// @param oracle The contract address of the oracle referenced by the pool
    /// @return pool The V1 pool contract address
    function verifyCallback(
        address factory,
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) internal view returns (IMarginalV1Pool pool) {
        return
            verifyCallback(
                factory,
                PoolAddress.getPoolKey(tokenA, tokenB, maintenance, oracle)
            );
    }

    /// @notice Returns the address of a valid Marginal V1 Pool
    /// @param factory The contract address of the Marginal V1 factory
    /// @param poolKey The identifying key of the V1 pool
    /// @return pool The V1 pool contract address
    function verifyCallback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool pool) {
        pool = IMarginalV1Pool(PoolAddress.getAddress(factory, poolKey));
        if (msg.sender != address(pool)) revert PoolNotSender();
    }

    /// @notice Returns the address of a valid Uniswap V3 Pool
    /// @param factory The contract address of the Marginal V1 factory
    /// @param poolKey The identifying key of the V1 pool
    /// @return uniswapV3Pool The Uniswap V3 pool oracle address associated with the V1 pool
    function verifyUniswapV3Callback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IUniswapV3Pool uniswapV3Pool) {
        PoolAddress.getAddress(factory, poolKey); // checks marginal pool active
        uniswapV3Pool = IUniswapV3Pool(poolKey.oracle);
        if (msg.sender != poolKey.oracle) revert OracleNotSender();
    }
}
