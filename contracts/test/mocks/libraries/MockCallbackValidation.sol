// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {CallbackValidation} from "../../../libraries/CallbackValidation.sol";
import {PoolAddress} from "../../../libraries/PoolAddress.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

contract MockCallbackValidation {
    function verifyCallback(
        address factory,
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) external view returns (IMarginalV1Pool pool) {
        return
            CallbackValidation.verifyCallback(
                factory,
                tokenA,
                tokenB,
                maintenance,
                oracle
            );
    }

    function verifyCallback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) external view returns (IMarginalV1Pool pool) {
        return CallbackValidation.verifyCallback(factory, poolKey);
    }
}
