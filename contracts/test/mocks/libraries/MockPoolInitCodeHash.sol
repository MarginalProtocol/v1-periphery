// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {MarginalV1Pool} from "@marginal/v1-core/contracts/MarginalV1Pool.sol";

contract MockPoolInitCodeHash {
    function poolInitCodeHash() external view returns (bytes32) {
        return keccak256(type(MarginalV1Pool).creationCode);
    }
}
