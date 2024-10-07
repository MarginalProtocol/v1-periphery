// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {PoolAddress} from "../libraries/PoolAddress.sol";

/// @title The interface of the oracle lens contract for Marginal v1 pools
/// @notice Quotes oracle related quantities for Marginal v1 pools
interface IOracle {
    /// @notice Returns the current pool sqrt price, oracle sqrt price, and the funding rate due to difference between the two
    /// @param poolKey The identifying key of the Marginal v1 pool
    /// @return sqrtPriceX96 The Marginal v1 pool current sqrt price
    /// @return oracleSqrtPriceX96 The oracle sqrt price averaged over pool constant `secondsAgo`
    /// @return fundingRatioX96 The current instantaneous funding rate over next funding period for long positions on the pool (zeroForOne = false)
    function sqrtPricesX96(
        PoolAddress.PoolKey memory poolKey
    )
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint160 oracleSqrtPriceX96,
            uint256 fundingRatioX96
        );

    /// @notice Returns the liquidation sqrt price of an existing position
    /// @param tokenId The NFT token id associated with the position
    /// @return The liquidation sqrt price X96 that oracle must reach for position to be unsafe
    function liquidationSqrtPriceX96(
        uint256 tokenId
    ) external view returns (uint160);

    /// @notice Returns the liquidation sqrt price for given position details
    /// @param zeroForOne Whether position settlement requires debt in of token0 for size + margin out of token1
    /// @param size The position size on the pool in the margin token
    /// @param debt The position debt owed to the pool in the non-margin token
    /// @param margin The margin backing the position on the pool
    /// @param maintenance The pool minimum maintenance requirement for leverage positions
    /// @return The liquidation sqrt price X96 that oracle must reach for position to be unsafe
    function liquidationSqrtPriceX96(
        bool zeroForOne,
        uint128 size,
        uint128 debt,
        uint128 margin,
        uint24 maintenance
    ) external view returns (uint160);

    /// @notice Returns the health factor of an existing position
    /// @return The health factor of the position multiplied by 1e18
    function healthFactor(uint256 tokenId) external view returns (uint256);

    /// @notice Returns the health factor for given position details
    /// @dev hf = (c_y + s_y) / ((1+M) * d_x * TWAP) when zeroForOne = true
    /// or hf = (c_x + s_x) * TWAP / ((1+M) * d_y) when zeroForOne = false
    /// @param zeroForOne Whether position settlement requires debt in of token0 for size + margin out of token1
    /// @param size The position size on the pool in the margin token
    /// @param debt The position debt owed to the pool in the non-margin token
    /// @param margin The margin backing the position on the pool
    /// @param maintenance The pool minimum maintenance requirement for leverage positions
    /// @param sqrtPriceX96 The oracle sqrt price averaged over pool constant `secondsAgo`
    /// @return The health factor for given position details multiplied by 1e18
    function healthFactor(
        bool zeroForOne,
        uint128 size,
        uint128 debt,
        uint128 margin,
        uint24 maintenance,
        uint160 sqrtPriceX96
    ) external view returns (uint256);
}
