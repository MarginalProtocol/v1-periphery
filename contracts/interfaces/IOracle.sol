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
    /// @return fundingSqrtRatioX96 The current instantaneous sqrt funding rate for long positions on the pool (zeroForOne = false)
    function sqrtPricesX96(
        PoolAddress.PoolKey memory poolKey
    )
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint160 oracleSqrtPriceX96,
            uint256 fundingSqrtRatioX96
        );

    /// @notice Returns the liquidation sqrt price of an existing position
    /// @param tokenId The NFT token id associated with the position
    /// @return The liquidation sqrt price X96 that oracle must reach for position to be unsafe
    function liquidationSqrtPriceX96(
        uint256 tokenId
    ) external view returns (uint160);
}
