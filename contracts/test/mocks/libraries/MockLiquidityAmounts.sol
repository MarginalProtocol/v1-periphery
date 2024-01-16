// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {LiquidityAmounts} from "../../../libraries/LiquidityAmounts.sol";

contract MockLiquidityAmounts {
    function getLiquidityForAmount0(
        uint160 sqrtPriceX96,
        uint256 amount0
    ) external pure returns (uint128) {
        return LiquidityAmounts.getLiquidityForAmount0(sqrtPriceX96, amount0);
    }

    function getLiquidityForAmount1(
        uint160 sqrtPriceX96,
        uint256 amount1
    ) external pure returns (uint128) {
        return LiquidityAmounts.getLiquidityForAmount1(sqrtPriceX96, amount1);
    }

    function getLiquidityForAmounts(
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1
    ) external pure returns (uint128) {
        return
            LiquidityAmounts.getLiquidityForAmounts(
                sqrtPriceX96,
                amount0,
                amount1
            );
    }
}
