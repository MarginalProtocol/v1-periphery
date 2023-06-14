// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity =0.8.15;

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import "../interfaces/IPeripheryImmutableState.sol";

/// @title Immutable state
/// @notice Immutable state used by periphery contracts
abstract contract PeripheryImmutableState is IPeripheryImmutableState {
    address public immutable factory;
    address public immutable deployer;
    address public immutable WETH9;

    constructor(address _factory, address _WETH9) {
        factory = _factory;
        deployer = IMarginalV1Factory(_factory).marginalV1Deployer();
        WETH9 = _WETH9;
    }
}
