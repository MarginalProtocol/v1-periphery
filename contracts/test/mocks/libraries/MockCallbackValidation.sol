// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {CallbackValidation} from "../../../libraries/CallbackValidation.sol";
import {PoolAddress} from "../../../libraries/PoolAddress.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

contract MockCallbackValidation {
    function verifyCallback(
        address deployer,
        address factory,
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) external view returns (IMarginalV1Pool pool) {
        return
            CallbackValidation.verifyCallback(
                deployer,
                factory,
                tokenA,
                tokenB,
                maintenance,
                oracle
            );
    }

    function verifyCallback(
        address deployer,
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) external view returns (IMarginalV1Pool pool) {
        return CallbackValidation.verifyCallback(deployer, factory, poolKey);
    }
}
