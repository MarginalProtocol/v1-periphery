// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {PoolAddress} from "../../../libraries/PoolAddress.sol";
import {MarginalV1Pool} from "@marginal/v1-core/contracts/MarginalV1Pool.sol";

contract MockPoolAddress {
    function getPoolKey(
        address tokenA,
        address tokenB,
        uint24 maintenance
    ) external pure returns (PoolAddress.PoolKey memory) {
        return PoolAddress.getPoolKey(tokenA, tokenB, maintenance);
    }

    function computeAddress(
        address deployer,
        address factory,
        PoolAddress.PoolKey memory key
    ) external pure returns (address) {
        return PoolAddress.computeAddress(deployer, factory, key);
    }

    function POOL_INIT_CODE_HASH() external pure returns (bytes32) {
        return PoolAddress.POOL_INIT_CODE_HASH;
    }

    function poolInitCodeHash() external view returns (bytes32) {
        return keccak256(type(MarginalV1Pool).creationCode);
    }
}
