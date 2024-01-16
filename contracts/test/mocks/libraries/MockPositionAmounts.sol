// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {PositionAmounts} from "../../../libraries/PositionAmounts.sol";

contract MockPositionAmounts {
    function getLiquidityForSize(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint24 maintenance,
        bool zeroForOne,
        uint128 size
    ) external pure returns (uint128) {
        return
            PositionAmounts.getLiquidityForSize(
                liquidity,
                sqrtPriceX96,
                maintenance,
                zeroForOne,
                size
            );
    }
}
