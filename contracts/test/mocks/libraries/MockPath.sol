// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {Path} from "../../../libraries/Path.sol";

contract MockPath {
    function hasMultiplePools(bytes memory path) external pure returns (bool) {
        return Path.hasMultiplePools(path);
    }

    function numPools(bytes memory path) external pure returns (uint256) {
        return Path.numPools(path);
    }

    function decodeFirstPool(
        bytes memory path
    )
        external
        pure
        returns (
            address tokenA,
            address tokenB,
            uint24 maintenance,
            address oracle
        )
    {
        return Path.decodeFirstPool(path);
    }

    function getFirstPool(
        bytes memory path
    ) external pure returns (bytes memory) {
        return Path.getFirstPool(path);
    }

    function skipToken(bytes memory path) external pure returns (bytes memory) {
        return Path.skipToken(path);
    }
}
