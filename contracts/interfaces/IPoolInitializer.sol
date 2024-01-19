// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

/// @title Interface for the Marginal v1 pool initializer
/// @notice Provides methods for preparing, creating and initializing a Marginal v1 pool
interface IPoolInitializer {
    struct CreateAndInitializeParams {
        address token0;
        address token1;
        uint24 maintenance;
        uint24 uniswapV3Fee;
        address recipient;
        uint160 sqrtPriceX96;
        uint160 sqrtPriceLimitX96;
        uint256 amount0BurnedMax;
        uint256 amount1BurnedMax;
        uint256 amount0Desired;
        uint256 amount1Desired;
        uint256 amount0Min;
        uint256 amount1Min;
        uint256 deadline;
    }

    /// @notice Creates a new pool if it does not exist, then initializes if not initialized
    /// @param params The parameters necessary to create and initialize a pool, encoded as `CreateAndInitializeParams` in calldata
    /// @return pool Returns the pool address based on the pair of tokens, Uniswap v3 fee, and maintenance, will return the newly created pool address if necessary
    /// @return shares The amount of shares minted to `params.recipient` after initializing pool with liquidity
    /// @return amount0 The amount of the input token0 to create and initialize pool
    /// @return amount1 The amount of the input token1 to create and initialize pool
    function createAndInitializePoolIfNecessary(
        CreateAndInitializeParams calldata params
    )
        external
        payable
        returns (address pool, uint256 shares, int256 amount0, int256 amount1);

    struct InitializePoolSqrtPriceX96Params {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint160 sqrtPriceX96;
        uint256 amountInMaximum;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
        uint256 deadline;
    }

    /// @notice Swaps through pool to set the pool price
    /// @dev Intended for pools with dust amounts of liquidity as otherwise amount in will be substantial
    /// @param params The parameters necessary to initialize pool with `params.sqrtPriceX96`
    /// @return amount0 The amount of the input token0 to set the price
    /// @return amount1 The amount of the input token1 to set the price
    function initializePoolSqrtPriceX96(
        InitializePoolSqrtPriceX96Params memory params
    ) external payable returns (int256 amount0, int256 amount1);

    struct InitializeOracleParams {
        address token0;
        address token1;
        uint24 maintenance;
        uint24 uniswapV3Fee;
        uint16 observationCardinalityNext;
    }

    /// @notice Increases observationCardinalityNext on oracle Uniswap v3 pool, if necessary, to prepare for Marginal v1 pool creation.
    /// @dev There will be a time lag between increasing observationCardinalityNext on the oracle pool and when observationCardinality on slot0 changes.
    /// @param params The parameters necessary to initialize oracle for pool, encoded as `InitializeOracleParams` in calldata
    function initializeOracleIfNecessary(
        InitializeOracleParams calldata params
    ) external;
}
