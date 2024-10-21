// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {PositionHealth} from "../../../libraries/PositionHealth.sol";

contract MockPositionHealth {
    function getHealthForPosition(
        bool zeroForOne,
        uint128 size,
        uint128 debt,
        uint128 margin,
        uint24 maintenance,
        uint160 sqrtPriceX96
    ) external pure returns (uint256) {
        return
            PositionHealth.getHealthForPosition(
                zeroForOne,
                size,
                debt,
                margin,
                maintenance,
                sqrtPriceX96
            );
    }
}
