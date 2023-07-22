// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity ^0.8.0;

import "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";
import "./PoolAddress.sol";

/// @notice Provides validation for callbacks from Marginal V1 Pools
/// @dev Fork of Uniswap V3 periphery CallbackValidation.sol
library CallbackValidation {
    error PoolNotSender();

    /// @notice Returns the address of a valid Marginal V1 Pool
    /// @param deployer The contract address of the Marginal V1 deployer
    /// @param factory The contract address of the Marginal V1 factory
    /// @param tokenA The contract address of either token0 or token1
    /// @param tokenB The contract address of the other token
    /// @param maintenance The maintenance requirements of the pool
    /// @param oracle The contract address of the oracle referenced by the pool
    /// @return pool The V1 pool contract address
    function verifyCallback(
        address deployer,
        address factory,
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) internal view returns (IMarginalV1Pool pool) {
        return
            verifyCallback(
                deployer,
                factory,
                PoolAddress.getPoolKey(tokenA, tokenB, maintenance, oracle)
            );
    }

    /// @notice Returns the address of a valid Marginal V1 Pool
    /// @param deployer The contract address of the Marginal V1 deployer
    /// @param factory The contract address of the Marginal V1 factory
    /// @param poolKey The identifying key of the V1 pool
    /// @return pool The V1 pool contract address
    function verifyCallback(
        address deployer,
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool pool) {
        pool = IMarginalV1Pool(
            PoolAddress.computeAddress(deployer, factory, poolKey)
        );
        if (msg.sender != address(pool)) revert PoolNotSender();
    }
}
