// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";

/// @title Position health library
/// @notice Calculates health of position from its attributes
library PositionHealth {
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
    function getHealthForPosition(
        bool zeroForOne,
        uint128 size,
        uint128 debt,
        uint128 margin,
        uint24 maintenance,
        uint160 sqrtPriceX96
    ) internal pure returns (uint256) {
        if (!zeroForOne) {
            uint256 debt1Adjusted = (uint256(debt) *
                (1e6 + uint256(maintenance))) / 1e6;
            uint256 liquidityCollateral = Math.mulDiv(
                uint256(margin) + uint256(size),
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            uint256 liquidityDebt = (debt1Adjusted << FixedPoint96.RESOLUTION) /
                sqrtPriceX96;
            return (
                liquidityDebt > 0
                    ? Math.mulDiv(liquidityCollateral, 1e18, liquidityDebt)
                    : (liquidityCollateral > 0 ? type(uint256).max : 0)
            );
        } else {
            uint256 debt0Adjusted = (uint256(debt) *
                (1e6 + uint256(maintenance))) / 1e6;
            uint256 liquidityCollateral = ((uint256(margin) + uint256(size)) <<
                FixedPoint96.RESOLUTION) / sqrtPriceX96;
            uint256 liquidityDebt = Math.mulDiv(
                debt0Adjusted,
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            return (
                liquidityDebt > 0
                    ? Math.mulDiv(liquidityCollateral, 1e18, liquidityDebt)
                    : (liquidityCollateral > 0 ? type(uint256).max : 0)
            );
        }
    }
}
