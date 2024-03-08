// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";

/// @title Position amounts library
/// @notice Calculates liquidity from desired size amounts
library PositionAmounts {
    using SafeCast for uint256;

    error SizeGreaterThanReserve(uint256 reserve);

    /// @notice Gets the pool liquidity to be utilized for a given position size
    /// @param liquidity The available liquidity of the pool
    /// @param sqrtPriceX96 The sqrt price of the pool
    /// @param maintenance The minimum maintenance requirement of the pool
    /// @param zeroForOne Whether long token1 and short token0 (true), or long token0 and short token1 (false)
    /// @param size The desired size of the position in token1 if zeroForOne = true, or token0 if zeroForOne = false
    /// @return liquidityDelta The pool liquidity to be utilized
    function getLiquidityForSize(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint24 maintenance,
        bool zeroForOne,
        uint128 size
    ) internal pure returns (uint128 liquidityDelta) {
        // del L / L = (sx / x) / (1 - (1 - sx / x) ** 2 / (1 + M))
        (uint256 reserve0, uint256 reserve1) = LiquidityMath.toAmounts(
            liquidity,
            sqrtPriceX96
        );
        uint256 reserve = !zeroForOne ? reserve0 : reserve1;
        if (size >= reserve) revert SizeGreaterThanReserve(reserve);

        uint256 prod = (reserve - uint256(size)) ** 2 / reserve;
        uint256 denom = reserve - (prod * 1e6) / (1e6 + maintenance);
        liquidityDelta = ((uint256(liquidity) * uint256(size)) / denom)
            .toUint128();
    }
}
