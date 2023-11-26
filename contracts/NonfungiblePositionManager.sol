// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PositionManagement} from "./base/PositionManagement.sol";
import {PositionState} from "./base/PositionState.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";
import {PositionAmounts} from "./libraries/PositionAmounts.sol";
import {INonfungiblePositionManager} from "./interfaces/INonfungiblePositionManager.sol";

contract NonfungiblePositionManager is
    INonfungiblePositionManager,
    Multicall,
    ERC721,
    PeripheryImmutableState,
    PositionManagement,
    PositionState,
    PeripheryValidation
{
    struct Position {
        address pool;
        uint96 id;
    }
    mapping(uint256 => Position) private _positions;

    uint256 private _nextId = 1;

    modifier onlyApprovedOrOwner(uint256 tokenId) {
        if (!_isApprovedOrOwner(msg.sender, tokenId)) revert Unauthorized();
        _;
    }

    event Mint(
        uint256 indexed tokenId,
        uint256 size,
        uint256 debt,
        uint256 amountIn
    );
    event Lock(uint256 indexed tokenId, uint256 marginAfter);
    event Free(uint256 indexed tokenId, uint256 marginAfter);
    event Burn(uint256 indexed tokenId, uint256 amountIn, uint256 amountOut);
    event Grab(uint256 indexed tokenId, uint256 rewards);

    error Unauthorized();
    error InvalidPoolKey();

    constructor(
        address _factory,
        address _WETH9
    )
        ERC721("Marginal V1 Position Token", "MRGLV1-POS")
        PeripheryImmutableState(_factory, _WETH9)
    {}

    /// @inheritdoc INonfungiblePositionManager
    function positions(
        uint256 tokenId
    )
        external
        view
        returns (
            address pool,
            uint96 positionId,
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            bool liquidated
        )
    {
        // TODO: check re-entrancy view issues
        Position memory position = _positions[tokenId];
        pool = position.pool;
        positionId = position.id;
        (zeroForOne, size, debt, margin, liquidated) = getPositionSynced(
            pool,
            address(this),
            positionId
        );
    }

    /// @inheritdoc INonfungiblePositionManager
    function mint(
        MintParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint256 tokenId, uint256 size, uint256 debt, uint256 amountIn)
    {
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (uint128 liquidity, uint160 sqrtPriceX96, , , , , , ) = pool.state();
        uint128 liquidityDelta = PositionAmounts.getLiquidityForSize(
            liquidity,
            sqrtPriceX96,
            params.maintenance,
            params.zeroForOne,
            params.sizeDesired
        );

        uint256 positionId;
        uint256 amount0;
        uint256 amount1;
        (positionId, size, debt, amount0, amount1) = open(
            OpenParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: address(this),
                zeroForOne: params.zeroForOne,
                liquidityDelta: liquidityDelta,
                sqrtPriceLimitX96: params.sqrtPriceLimitX96 == 0
                    ? (
                        params.zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : params.sqrtPriceLimitX96,
                margin: params.margin,
                sizeMinimum: params.sizeMinimum,
                debtMaximum: params.debtMaximum == 0
                    ? type(uint128).max
                    : params.debtMaximum,
                amountInMaximum: params.amountInMaximum == 0
                    ? type(uint256).max
                    : params.amountInMaximum
            })
        );
        amountIn = amount0 > 0 ? amount0 : amount1;

        _mint(params.recipient, (tokenId = _nextId++));

        _positions[tokenId] = Position({
            pool: address(pool),
            id: uint96(positionId)
        });

        emit Mint(tokenId, size, debt, amountIn);
    }

    /// @inheritdoc INonfungiblePositionManager
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
                        maintenance: params.maintenance,
                        oracle: params.oracle
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (uint256 margin0, uint256 margin1) = adjust(
            AdjustParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: params.recipient,
                id: position.id,
                marginDelta: int128(params.marginIn)
            })
        );
        margin = margin0 > 0 ? margin0 : margin1;

        emit Lock(params.tokenId, margin);
    }

    /// @inheritdoc INonfungiblePositionManager
    function free(
        FreeParams calldata params
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
                        maintenance: params.maintenance,
                        oracle: params.oracle
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (uint256 margin0, uint256 margin1) = adjust(
            AdjustParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: params.recipient,
                id: position.id,
                marginDelta: -int128(params.marginOut)
            })
        );
        margin = margin0 > 0 ? margin0 : margin1;

        emit Free(params.tokenId, margin);
    }

    /// @inheritdoc INonfungiblePositionManager
    function burn(
        BurnParams calldata params
    )
        external
        payable
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
                        maintenance: params.maintenance,
                        oracle: params.oracle
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (int256 amount0, int256 amount1) = settle(
            SettleParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
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

    /// @inheritdoc INonfungiblePositionManager
    function grab(
        GrabParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint256 rewards)
    {
        Position memory position = _positions[params.tokenId];
        if (
            address(
                getPool(
                    PoolAddress.PoolKey({
                        token0: params.token0,
                        token1: params.token1,
                        maintenance: params.maintenance,
                        oracle: params.oracle
                    })
                )
            ) != position.pool
        ) revert InvalidPoolKey();

        (uint256 rewards0, uint256 rewards1) = liquidate(
            LiquidateParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: params.recipient,
                owner: address(this),
                id: position.id
            })
        );
        rewards = rewards0 > 0 ? rewards0 : rewards1;

        emit Grab(params.tokenId, rewards);
    }
}
