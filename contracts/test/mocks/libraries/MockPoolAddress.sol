// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {PoolAddress} from "../../../libraries/PoolAddress.sol";

contract MockPoolAddress {
    function getPoolKey(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) external pure returns (PoolAddress.PoolKey memory) {
        return PoolAddress.getPoolKey(tokenA, tokenB, maintenance, oracle);
    }

    function getAddress(
        address factory,
        PoolAddress.PoolKey memory key
    ) external view returns (address) {
        return PoolAddress.getAddress(factory, key);
    }
}
