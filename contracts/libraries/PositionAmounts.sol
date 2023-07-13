// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";

library PositionAmounts {
    using SafeCast for uint256;

    error SizeGreaterThanReserve(uint128 reserve);

    function getLiquidityForSize(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint24 maintenance,
        bool zeroForOne,
        uint128 size
    ) internal pure returns (uint128 liquidityDelta) {
        // del L / L = (sx / x) / (1 - (1 - sx / x) ** 2 / (1 + M))
        (uint128 reserve0, uint128 reserve1) = LiquidityMath.toAmounts(
            liquidity,
            sqrtPriceX96
        );
        uint128 reserve = !zeroForOne ? reserve0 : reserve1;
        if (size >= reserve) revert SizeGreaterThanReserve(reserve);

        uint256 prod = uint256(reserve - size) ** 2 / uint256(reserve);
        uint256 denom = uint256(reserve) - (prod * 1e6) / (1e6 + maintenance);
        liquidityDelta = ((uint256(liquidity) * uint256(size)) / denom)
            .toUint128();
    }
}
