// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";

library PositionAmounts {
    using SafeCast for uint256;

    error SizeGreaterThanReserve(uint256 reserve);

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
