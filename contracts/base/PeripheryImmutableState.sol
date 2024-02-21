// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity =0.8.15;

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import "../interfaces/IPeripheryImmutableState.sol";

/// @title Immutable state
/// @notice Immutable state used by periphery contracts
abstract contract PeripheryImmutableState is IPeripheryImmutableState {
    address public immutable factory;
    address public immutable uniswapV3Factory;
    address public immutable WETH9;

    constructor(address _factory, address _WETH9) {
        factory = _factory;
        uniswapV3Factory = IMarginalV1Factory(_factory).uniswapV3Factory();
        WETH9 = _WETH9;
    }
}
