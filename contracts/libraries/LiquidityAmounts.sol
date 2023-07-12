// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";

library LiquidityAmounts {
    using SafeCast for uint256;

    function getLiquidityForAmount0(
        uint160 sqrtPriceX96,
        uint256 amount0
    ) internal pure returns (uint128) {
        return
            (Math.mulDiv(amount0, sqrtPriceX96, FixedPoint96.Q96)).toUint128();
    }

    function getLiquidityForAmount1(
        uint160 sqrtPriceX96,
        uint256 amount1
    ) internal pure returns (uint128) {
        return
            ((amount1 << FixedPoint96.RESOLUTION) / sqrtPriceX96).toUint128();
    }

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
