// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity =0.8.15;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PositionManagement} from "./base/PositionManagement.sol";
import {INonfungiblePositionManager} from "./interfaces/INonfungiblePositionManager.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";

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
        uint96 id;
    }
    mapping(uint256 => Position) private _positions;

    mapping(address => PoolAddress.PoolKey) private _pools;

    uint256 private _nextId = 1;

    modifier onlyApprovedOrOwner(uint256 tokenId) {
        if (!_isApprovedOrOwner(msg.sender, tokenId)) revert Unauthorized();
        _;
    }

    event Mint(uint256 indexed tokenId, uint256 size);
    event Lock(uint256 indexed tokenId, uint256 marginAfter);
    event Free(uint256 indexed tokenId, uint256 marginAfter);
    event Burn(uint256 indexed tokenId, uint256 amountIn, uint256 amountOut);

    error Unauthorized();
    error InvalidPoolKey();

    constructor(
        address _factory,
        address _WETH9
    )
        ERC721("Marginal V1 Position Token", "MRGLV1-POS")
        PeripheryImmutableState(_factory, _WETH9)
    {}

    function cachePoolKey(
        address pool,
        PoolAddress.PoolKey memory poolKey
    ) private {
        if (_pools[pool].token0 == address(0)) {
            _pools[pool] = poolKey;
        }
    }

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

    /// @notice Mints a new position, opening on pool
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
        (positionId, size, pool) = open(
            OpenParams({
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
            id: uint96(positionId)
        });

        cachePoolKey(
            address(pool),
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance
            })
        );

        emit Mint(tokenId, size);
    }

    struct LockParams {
        address token0;
        address token1;
        uint24 maintenance;
        uint256 tokenId;
        uint128 marginIn;
        address recipient;
        uint256 deadline;
    }

    /// @dev Adds margin to an existing position
    function lock(
        LockParams calldata params
    )
        external
        payable
        onlyApprovedOrOwner(params.tokenId)
        checkDeadline(params.deadline)
        returns (uint256 margin)
    {
        Position memory position = _positions[params.tokenId];
        if (
            address(
                getPool(
                    PoolAddress.PoolKey({
                        token0: params.token0,
                        token1: params.token1,
                        maintenance: params.maintenance
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (uint256 margin0, uint256 margin1) = adjust(
            AdjustParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                recipient: params.recipient,
                id: position.id,
                marginDelta: int128(params.marginIn)
            })
        );
        margin = margin0 > 0 ? margin0 : margin1;

        emit Lock(params.tokenId, margin);
    }

    struct FreeParams {
        address token0;
        address token1;
        uint24 maintenance;
        uint256 tokenId;
        uint128 marginOut;
        address recipient;
        uint256 deadline;
    }

    /// @notice Removes margin from an existing position
    function free(
        FreeParams calldata params
    )
        external
        onlyApprovedOrOwner(params.tokenId)
        checkDeadline(params.deadline)
        returns (uint256 margin)
    {
        Position memory position = _positions[params.tokenId];
        if (
            address(
                getPool(
                    PoolAddress.PoolKey({
                        token0: params.token0,
                        token1: params.token1,
                        maintenance: params.maintenance
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (uint256 margin0, uint256 margin1) = adjust(
            AdjustParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                recipient: params.recipient,
                id: position.id,
                marginDelta: -int128(params.marginOut)
            })
        );
        margin = margin0 > 0 ? margin0 : margin1;

        emit Free(params.tokenId, margin);
    }

    struct BurnParams {
        address token0;
        address token1;
        uint24 maintenance;
        uint256 tokenId;
        address recipient;
        uint256 deadline;
    }

    /// @notice Burns an existing position, settling on pool
    function burn(
        BurnParams calldata params
    )
        external
        onlyApprovedOrOwner(params.tokenId)
        checkDeadline(params.deadline)
        returns (uint256 amountIn, uint256 amountOut)
    {
        Position memory position = _positions[params.tokenId];
        if (
            address(
                getPool(
                    PoolAddress.PoolKey({
                        token0: params.token0,
                        token1: params.token1,
                        maintenance: params.maintenance
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (int256 amount0, int256 amount1) = settle(
            SettleParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                recipient: params.recipient,
                id: position.id
            })
        );
        amountIn = amount0 > 0
            ? uint256(amount0)
            : (amount1 > 0 ? uint256(amount1) : 0);
        amountOut = amount0 < 0
            ? uint256(-amount0)
            : (amount1 < 0 ? uint256(-amount1) : 0);

        delete _positions[params.tokenId];

        _burn(params.tokenId);

        emit Burn(params.tokenId, amountIn, amountOut);
    }
}
