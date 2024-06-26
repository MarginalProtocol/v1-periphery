// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;
pragma abicoder v2;

/// @title The interface for the Marginal v1 router
/// @notice Facilitates swaps and liquidity provision on Marginal v1 pools
interface IRouter {
    event IncreaseLiquidity(
        uint256 shares,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );
    event DecreaseLiquidity(
        uint256 shares,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );

    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    /// @notice Swaps `amountIn` of one token for as much as possible of another token
    /// @param params The parameters necessary for the swap, encoded as `ExactInputSingleParams` in calldata
    /// @return amountOut The amount of the received token
    function exactInputSingle(
        ExactInputSingleParams calldata params
    ) external payable returns (uint256 amountOut);

    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }

    /// @notice Swaps `amountIn` of one token for as much as possible of another along the specified path
    /// @param params The parameters necessary for the multi-hop swap, encoded as `ExactInputParams` in calldata
    /// @return amountOut The amount of the received token
    function exactInput(
        ExactInputParams calldata params
    ) external payable returns (uint256 amountOut);

    struct ExactOutputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint256 deadline;
        uint256 amountOut;
        uint256 amountInMaximum;
        uint160 sqrtPriceLimitX96;
    }

    /// @notice Swaps as little as possible of one token for `amountOut` of another token
    /// @dev If a contract sending in native (gas) token, `msg.sender` must implement a `receive()` function to receive any refunded unspent amount in.
    /// @param params The parameters necessary for the swap, encoded as `ExactOutputSingleParams` in calldata
    /// @return amountIn The amount of the input token
    function exactOutputSingle(
        ExactOutputSingleParams calldata params
    ) external payable returns (uint256 amountIn);

    struct ExactOutputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountOut;
        uint256 amountInMaximum;
    }

    /// @notice Swaps as little as possible of one token for `amountOut` of another along the specified path (reversed)
    /// @dev If a contract sending in native (gas) token, `msg.sender` must implement a `receive()` function to receive any refunded unspent amount in.
    /// @param params The parameters necessary for the multi-hop swap, encoded as `ExactOutputParams` in calldata
    /// @return amountIn The amount of the input token
    function exactOutput(
        ExactOutputParams calldata params
    ) external payable returns (uint256 amountIn);

    /// @notice Adds liquidity, minting on pool
    /// @dev If a contract sending in native (gas) token, `msg.sender` must implement a `receive()` function to receive any refunded unspent amount in.
    /// @param params The parameters necessary for adding liquidity, encoded as `AddLiquidityParams` in calldata
    /// @return shares The amount of shares minted
    /// @return amount0 The amount of the input token0
    /// @return amount1 The amount of the input token1
    function addLiquidity(
        AddLiquidityParams calldata params
    )
        external
        payable
        returns (uint256 shares, uint256 amount0, uint256 amount1);

    struct AddLiquidityParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint256 amount0Desired;
        uint256 amount1Desired;
        uint256 amount0Min;
        uint256 amount1Min;
        uint256 deadline;
    }

    /// @notice Removes liquidity, burning on pool
    /// @param params The parameters necessary for removing liquidity, encoded as `RemoveLiquidityParams` in calldata
    /// @return liquidityDelta The amount of liquidity removed
    /// @return amount0 The amount of the output token0
    /// @return amount1 The amount of the output token1
    function removeLiquidity(
        RemoveLiquidityParams calldata params
    )
        external
        payable
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1);

    struct RemoveLiquidityParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint256 shares;
        uint256 amount0Min;
        uint256 amount1Min;
        uint256 deadline;
    }
}
