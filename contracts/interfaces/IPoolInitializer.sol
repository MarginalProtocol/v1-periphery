// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;
pragma abicoder v2;

/// @title Initializes Uniswap v3 oracles to prepare creation of Marginal v1 pools
/// @notice Provides a method for initializing a Uniswap v3 oracle, if necessary, for bundling with other methods that
/// require the Marginal v1 pool to exist.
interface IPoolInitializer {
    /// @notice Increases observationCardinalityNext on oracle Uniswap v3 pool, if necessary, to prepare for Marginal v1 pool creation.
    /// @dev There will be a time lag between increasing observationCardinalityNext on the oracle pool and when observationCardinality on slot0 changes.
    /// @param token0 The contract address of token0 of the pool
    /// @param token1 The contract address of token1 of the pool
    /// @param maintenance The maintenance amount of the Marginal v1 pool for the specified token pair
    /// @param uniswapV3Fee The fee amount of the Uniswap v3 pool for the specified token pair used as the oracle reference
    /// @param observationCardinalityNext The next observation cardinality of the Uniswap v3 pool for the specified token pair
    function initializeOracleIfNecessary(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 uniswapV3Fee,
        uint16 observationCardinalityNext
    ) external;
}
