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
    struct Position {
        address pool;
        uint96 id; // TODO: change on v1 core and add initialized bool for packing
    }
    mapping(uint256 => Position) private _positions;

    uint256 private _nextId = 1;

    event Mint(uint256 indexed tokenId, uint256 size);

    constructor(
        address _factory,
        address _WETH9
    )
        ERC721("Marginal V1 Position Token", "MRGLV1-POS")
        PeripheryImmutableState(_factory, _WETH9)
    {}

    struct MintParams {
        address token0;
        address token1;
        uint24 maintenance;
        bool zeroForOne;
        uint128 liquidityDelta;
        uint160 sqrtPriceLimitX96;
        uint128 margin;
        uint256 sizeMinimum;
        address recipient;
        uint256 deadline;
    }

    function mint(
        MintParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint256 tokenId, uint256 size)
    {
        IMarginalV1Pool pool;
        uint256 positionId;
        (positionId, size, pool) = openPosition(
            OpenPositionParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                recipient: address(this),
                zeroForOne: params.zeroForOne,
                liquidityDelta: params.liquidityDelta,
                sqrtPriceLimitX96: params.sqrtPriceLimitX96,
                margin: params.margin,
                sizeMinimum: params.sizeMinimum
            })
        );

        _mint(params.recipient, (tokenId = _nextId++));

        _positions[tokenId] = Position({
            pool: address(pool),
            id: uint96(positionId) // TODO: change from 104 to 96 on v1 core
        });

        emit Mint(tokenId, size);
    }
}
