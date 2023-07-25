// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;
pragma abicoder v2;

/// @title Creates and initializes V3 Pools
/// @notice Provides a method for creating and initializing a pool, if necessary, for bundling with other methods that
/// require the pool to exist.
interface IPoolInitializer {
    /// @notice Creates a new pool if it does not exist, then initializes if not initialized
    /// @dev This method can be bundled with others via IMulticall for the first action (e.g. mint) performed against a pool
    /// @param token0 The contract address of token0 of the pool
    /// @param token1 The contract address of token1 of the pool
    /// @param maintenance The maintenance amount of the Marginal v1 pool for the specified token pair
    /// @param uniswapV3Fee The fee amount of the Uniswap v3 pool for the specified token pair used as the oracle reference
    /// @param sqrtPriceX96 The initial square root price of the pool as a Q64.96 value
    /// @return pool Returns the pool address based on the pair of tokens, Uniswap v3 fee, and maintenance, will return the newly created pool address if necessary
    function createAndInitializePoolIfNecessary(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 uniswapV3Fee,
        uint160 sqrtPriceX96
    ) external payable returns (address pool);

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
