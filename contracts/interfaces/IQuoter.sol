// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {INonfungiblePositionManager} from "./INonfungiblePositionManager.sol";
import {IRouter} from "./IRouter.sol";

interface IQuoter {
    /// @notice Quotes the position result of NonfungiblePositionManager::mint
    /// @param params Param inputs to NonfungiblePositionManager::mint
    /// @dev Reverts if mint would revert
    /// @return size Position size in units of amount1 if zeroForOne == true else units of amount0
    /// @return debt Position debt in units of amount0 if zeroForOne == true else units of amount1
    /// @return amountIn Amount of margin token in required to open position, includes fees and liquidation rewards set aside in pool
    /// @return liquidityAfter Pool liquidity after mint
    /// @return sqrtPriceX96After Pool sqrt price after mint
    function quoteMint(
        INonfungiblePositionManager.MintParams calldata params
    )
        external
        view
        returns (
            uint256 size,
            uint256 debt,
            uint256 amountIn,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        );

    /// @notice Quotes the amountOut result of Router::exactInputSingle
    /// @param params Param inputs to Router::exactInputSingle
    /// @dev Reverts if exactInputSingle would revert
    /// @return amountOut Amount of token received from pool after swap
    /// @return liquidityAfter Pool liquidity after swap
    /// @return sqrtPriceX96After Pool sqrt price after swap
    function quoteExactInputSingle(
        IRouter.ExactInputSingleParams calldata params
    )
        external
        view
        returns (
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        );

    /// @notice Quotes the amountOut result of Router::exactInput
    /// @param params Param inputs to Router::exactInput
    /// @dev Reverts if exactInput would revert
    /// @return amountOut Amount of token received from pool after swap
    /// @return liquiditiesAfter Pool liquidities after swap
    /// @return sqrtPricesX96After Pool sqrt prices after swap
    function quoteExactInput(
        IRouter.ExactInputParams calldata params
    )
        external
        view
        returns (
            uint256 amountOut,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        );

    /// @notice Quotes the amountIn result of Router::exactOutputSingle
    /// @param params Param inputs to Router::exactOutputSingle
    /// @dev Reverts if exactOutputSingle would revert
    /// @return amountIn Amount of token sent to pool for swap
    /// @return liquidityAfter Pool liquidity after swap
    /// @return sqrtPriceX96After Pool sqrt price after swap
    function quoteExactOutputSingle(
        IRouter.ExactOutputSingleParams calldata params
    )
        external
        view
        returns (
            uint256 amountIn,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        );

    /// @notice Quotes the amountIn result of Router::exactOutput
    /// @param params Param inputs to Router::exactOutput
    /// @dev Reverts if exactOutput would revert
    /// @return amountIn Amount of token sent to pool for swap
    /// @return liquiditiesAfter Pool liquidities after swap
    /// @return sqrtPricesX96After Pool sqrt prices after swap
    function quoteExactOutput(
        IRouter.ExactOutputParams calldata params
    )
        external
        view
        returns (
            uint256 amountIn,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        );

    /// @notice Quotes the amounts in result of Router::addLiquidity
    /// @param params Param inputs to Router::addLiquidity
    /// @dev Reverts if addLiquidity would revert
    /// @return shares Amount of lp token minted by pool
    /// @return amount0 Amount of token0 sent to pool for adding liquidity
    /// @return amount1 Amount of token1 sent to pool for adding liquidity
    /// @return liquidityAfter Pool liquidity after adding liquidity
    function quoteAddLiquidity(
        IRouter.AddLiquidityParams memory params
    )
        external
        view
        returns (
            uint256 shares,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidityAfter
        );

    /// @notice Quotes the amounts in result of Router::removeLiquidity
    /// @param params Param inputs to Router::removeLiquidity
    /// @dev Reverts if removeLiquidity would revert
    /// @return liquidityDelta Amount of liquidity removed from pool
    /// @return amount0 Amount of token0 received from pool for removing liquidity
    /// @return amount1 Amount of token1 received from pool for removing liquidity
    /// @return liquidityAfter Pool liquidity after removing liquidity
    function quoteRemoveLiquidity(
        IRouter.RemoveLiquidityParams memory params
    )
        external
        view
        returns (
            uint256 liquidityDelta,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidityAfter
        );
}
