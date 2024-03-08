// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";

/// @title Liquidity amounts library
/// @notice Calculates liquidity from desired reserve amounts
library LiquidityAmounts {
    using SafeCast for uint256;

    /// @notice Gets the pool liquidity contribution for a given amount of token0
    /// @param sqrtPriceX96 The sqrt price of the pool
    /// @param amount0 The amount of token0
    /// @return The liquidity contribution
    function getLiquidityForAmount0(
        uint160 sqrtPriceX96,
        uint256 amount0
    ) internal pure returns (uint128) {
        return
            (Math.mulDiv(amount0, sqrtPriceX96, FixedPoint96.Q96)).toUint128();
    }

    /// @notice Gets the pool liquidity contribution for a given amount of token1
    /// @param sqrtPriceX96 The sqrt price of the pool
    /// @param amount1 The amount of token1
    /// @return The liquidity contribution
    function getLiquidityForAmount1(
        uint160 sqrtPriceX96,
        uint256 amount1
    ) internal pure returns (uint128) {
        return
            ((amount1 << FixedPoint96.RESOLUTION) / sqrtPriceX96).toUint128();
    }

    /// @notice Gets the pool liquidity contribution for given amounts of token0 and token1
    /// @dev Takes the minimum of contributions from either token0 or token1
    /// @param sqrtPriceX96 The sqrt price of the pool
    /// @param amount0 The amount of token0
    /// @param amount1 The amount of token1
    /// @return liquidity The liquidity contribution
    function getLiquidityForAmounts(
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1
    ) internal pure returns (uint128 liquidity) {
        uint128 liquidity0 = getLiquidityForAmount0(sqrtPriceX96, amount0);
        uint128 liquidity1 = getLiquidityForAmount1(sqrtPriceX96, amount1);

        liquidity = liquidity0 < liquidity1 ? liquidity0 : liquidity1;
    }
}
