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
}
