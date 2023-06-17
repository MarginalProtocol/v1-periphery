// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity =0.8.15;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PositionManagement} from "./base/PositionManagement.sol";
import {INonfungiblePositionManager} from "./interfaces/INonfungiblePositionManager.sol";

// TODO: INonfungiblePositionManager
contract NonfungiblePositionManager is
    Multicall,
    ERC721,
    PeripheryImmutableState,
    PositionManagement,
    PeripheryValidation
{
    constructor(
        address _factory,
        address _WETH9
    )
        ERC721("Marginal V1 Position Token", "MRGLV1-POS")
        PeripheryImmutableState(_factory, _WETH9)
    {}
}
