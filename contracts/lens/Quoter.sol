// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {Position as PositionLibrary} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {OracleLibrary} from "@marginal/v1-core/contracts/libraries/OracleLibrary.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";
import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {LiquidityAmounts} from "../libraries/LiquidityAmounts.sol";
import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PositionState} from "../base/PositionState.sol";
import {Path} from "../libraries/Path.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";
import {PositionAmounts} from "../libraries/PositionAmounts.sol";

import {INonfungiblePositionManager} from "../interfaces/INonfungiblePositionManager.sol";
import {IRouter} from "../interfaces/IRouter.sol";
import {IUniswapV3StaticQuoter} from "../interfaces/IUniswapV3StaticQuoter.sol";
import {IQuoter} from "../interfaces/IQuoter.sol";

/// @title Quoter for Marginal v1 pools
/// @notice Quotes the result of leverage trades and swaps on Marginal v1 pools
contract Quoter is
    IQuoter,
    PeripheryImmutableState,
    PeripheryValidation,
    PositionState,
    Multicall
{
    using Path for bytes;

    INonfungiblePositionManager public immutable manager;
    IUniswapV3StaticQuoter public immutable uniswapV3Quoter;

    constructor(
        address _factory,
        address _WETH9,
        address _manager,
        address _uniswapV3Quoter
    ) PeripheryImmutableState(_factory, _WETH9) {
        manager = INonfungiblePositionManager(_manager);
        uniswapV3Quoter = IUniswapV3StaticQuoter(_uniswapV3Quoter);
    }

    /// @dev Returns the pool for the given token pair and maintenance. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool) {
        return IMarginalV1Pool(PoolAddress.getAddress(factory, poolKey));
    }

    /// @inheritdoc IQuoter
    function quoteMint(
        INonfungiblePositionManager.MintParams calldata params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 size,
            uint256 debt,
            uint256 margin,
            uint256 safeMarginMinimum,
            uint256 fees,
            bool safe,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            uint128 liquidityLockedAfter
        )
    {
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            int24 tick,
            ,
            ,
            uint8 feeProtocol,
            bool initialized
        ) = pool.state();
        if (!initialized) revert("Not initialized");

        uint128 liquidityDelta = PositionAmounts.getLiquidityForSize(
            liquidity,
            sqrtPriceX96,
            params.maintenance,
            params.zeroForOne,
            params.sizeDesired
        );
        if (
            liquidityDelta == 0 ||
            liquidityDelta + PoolConstants.MINIMUM_LIQUIDITY >= liquidity
        ) revert("Invalid liquidityDelta");

        uint160 sqrtPriceLimitX96 = params.sqrtPriceLimitX96 == 0
            ? (
                params.zeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
            : params.sqrtPriceLimitX96;
        if (
            params.zeroForOne
                ? !(sqrtPriceLimitX96 < sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceLimitX96");

        uint128 debtMaximum = params.debtMaximum == 0
            ? type(uint128).max
            : params.debtMaximum;

        uint256 amountInMaximum = params.amountInMaximum == 0
            ? type(uint256).max
            : params.amountInMaximum;

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextOpen(
            liquidity,
            sqrtPriceX96,
            liquidityDelta,
            params.zeroForOne,
            params.maintenance
        );
        if (
            params.zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert("sqrtPriceX96Next exceeds limit");

        // @dev ignore tick cumulatives and timestamps on position assemble
        PositionLibrary.Info memory position = PositionLibrary.assemble(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            params.zeroForOne,
            tick,
            0,
            0,
            0
        );
        if (
            position.size < PoolConstants.MINIMUM_SIZE ||
            position.debt0 < PoolConstants.MINIMUM_SIZE ||
            position.debt1 < PoolConstants.MINIMUM_SIZE ||
            position.insurance0 < PoolConstants.MINIMUM_SIZE ||
            position.insurance1 < PoolConstants.MINIMUM_SIZE
        ) revert("Invalid position");

        uint128 marginMinimum = PositionLibrary.marginMinimum(
            position,
            params.maintenance
        );
        if (marginMinimum == 0 || params.margin < marginMinimum)
            revert("Margin less than min");
        position.margin = params.margin;

        size = position.size;
        if (size < params.sizeMinimum) revert("Size less than min");

        debt = params.zeroForOne ? position.debt0 : position.debt1;
        if (debt > debtMaximum) revert("Debt greater than max");

        margin = params.margin;
        fees = PositionLibrary.fees(position.size, PoolConstants.fee);

        uint256 amountIn = margin + fees;
        if (amountIn > amountInMaximum) revert("amountIn greater than max");

        // account for protocol fees *after* since taken from fees once transferred to pool
        uint256 _fees = fees;
        if (feeProtocol > 0) _fees -= uint256(_fees / feeProtocol);

        (liquidityAfter, sqrtPriceX96After) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                !params.zeroForOne ? int256(_fees) : int256(0),
                !params.zeroForOne ? int256(0) : int256(_fees)
            );

        uint128 liquidityLocked = pool.liquidityLocked();
        liquidityLockedAfter = liquidityLocked + liquidityDelta;

        // check whether position would be safe after open given twap oracle lag
        {
            int56[] memory oracleTickCumulativesLast = getOracleSynced(
                address(pool)
            );
            int56 oracleTickCumulativeDelta = OracleLibrary
                .oracleTickCumulativeDelta(
                    oracleTickCumulativesLast[0],
                    oracleTickCumulativesLast[1]
                );

            safe = PositionLibrary.safe(
                position,
                OracleLibrary.oracleSqrtPriceX96(
                    oracleTickCumulativeDelta,
                    PoolConstants.secondsAgo
                ),
                params.maintenance
            );
            safeMarginMinimum = _safeMarginMinimum(
                position,
                params.maintenance,
                oracleTickCumulativeDelta
            );
        }
    }

    /// @notice Gets the pool position info synced for funding
    /// @param pool The address of the pool position is on
    /// @param positionId The ID of the pool position
    /// @param blockTimestampLast The last synced Marginal v1 pool timestamp
    /// @param tickCumulativeLast The last synced Marginal v1 pool tick cumulative
    /// @param oracleTickCumulativeLast The last synced Uniswap v3 oracle pool tick cumulative
    /// @return position The synced pool position info
    function _getPositionInfoSynced(
        address pool,
        uint96 positionId,
        uint32 blockTimestampLast,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast
    ) internal view returns (PositionLibrary.Info memory position) {
        bytes32 key = keccak256(abi.encodePacked(address(manager), positionId));
        (
            uint128 _size,
            uint128 _debt0,
            uint128 _debt1,
            uint128 _insurance0,
            uint128 _insurance1,
            bool _zeroForOne,
            bool _liquidated,
            int24 _tick,
            uint32 _blockTimestamp,
            int56 _tickCumulativeDelta,
            uint128 _margin,
            uint128 _liquidityLocked,
            uint256 _rewards
        ) = IMarginalV1Pool(pool).positions(key);

        position = PositionLibrary.Info({
            size: _size,
            debt0: _debt0,
            debt1: _debt1,
            insurance0: _insurance0,
            insurance1: _insurance1,
            zeroForOne: _zeroForOne,
            liquidated: _liquidated,
            tick: _tick,
            blockTimestamp: _blockTimestamp,
            tickCumulativeDelta: _tickCumulativeDelta,
            margin: _margin,
            liquidityLocked: _liquidityLocked,
            rewards: _rewards
        });

        if (position.size > 0) {
            PositionLibrary.sync(
                position,
                blockTimestampLast,
                tickCumulativeLast,
                oracleTickCumulativeLast,
                PoolConstants.tickCumulativeRateMax,
                PoolConstants.fundingPeriod
            );
        }
    }

    /// @inheritdoc IQuoter
    function quoteBurn(
        INonfungiblePositionManager.BurnParams calldata params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint256 amountOut,
            uint256 rewards,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            uint128 liquidityLockedAfter
        )
    {
        (, uint96 positionId, , , , , , , , ) = manager.positions(
            params.tokenId
        );
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestampLast,
            int56 tickCumulativeLast,
            ,

        ) = getStateSynced(address(pool));
        int56[] memory oracleTickCumulativesLast = getOracleSynced(
            address(pool)
        );
        PositionLibrary.Info memory position = _getPositionInfoSynced(
            address(pool),
            positionId,
            blockTimestampLast,
            tickCumulativeLast,
            oracleTickCumulativesLast[1] // zero seconds ago
        );
        if (position.size == 0) revert("Invalid position");

        uint128 liquidityLocked = pool.liquidityLocked();
        liquidityLockedAfter = liquidityLocked - position.liquidityLocked;
        (uint256 amount0Unlocked, uint256 amount1Unlocked) = PositionLibrary
            .amountsLocked(position);

        rewards = position.rewards;

        int256 amount0;
        int256 amount1;
        if (!position.zeroForOne) {
            amount0 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out
            amount1 = int256(uint256(position.debt1)); // debt in

            (liquidityAfter, sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    liquidity,
                    sqrtPriceX96,
                    int256(
                        amount0Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
                    ), // insurance0 + debt0
                    int256(amount1Unlocked) + amount1 // insurance1 + debt1
                );
        } else {
            amount0 = int256(uint256(position.debt0)); // debt in
            amount1 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out

            (liquidityAfter, sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    liquidity,
                    sqrtPriceX96,
                    int256(amount0Unlocked) + amount0, // insurance0 + debt0
                    int256(
                        amount1Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
                    ) // insurance1 + debt1
                );
        }

        amountIn = amount0 > 0
            ? uint256(amount0)
            : (amount1 > 0 ? uint256(amount1) : 0);
        amountOut = amount0 < 0
            ? uint256(-amount0)
            : (amount1 < 0 ? uint256(-amount1) : 0);
    }

    /// @inheritdoc IQuoter
    function quoteIgnite(
        INonfungiblePositionManager.IgniteParams calldata params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountOut,
            uint256 rewards,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            uint128 liquidityLockedAfter
        )
    {
        (, uint96 positionId, , , , , , , , ) = manager.positions(
            params.tokenId
        );
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestampLast,
            int56 tickCumulativeLast,
            ,

        ) = getStateSynced(address(pool));
        int56[] memory oracleTickCumulativesLast = getOracleSynced(
            address(pool)
        );
        PositionLibrary.Info memory position = _getPositionInfoSynced(
            address(pool),
            positionId,
            blockTimestampLast,
            tickCumulativeLast,
            oracleTickCumulativesLast[1] // zero seconds ago
        );
        if (position.size == 0) revert("Invalid position");

        uint128 liquidityLocked = pool.liquidityLocked();
        liquidityLockedAfter = liquidityLocked - position.liquidityLocked;
        (uint256 amount0Unlocked, uint256 amount1Unlocked) = PositionLibrary
            .amountsLocked(position);

        rewards = position.rewards;

        int256 amount0;
        int256 amount1;
        if (!position.zeroForOne) {
            amount0 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out
            amount1 = int256(uint256(position.debt1)); // debt in

            (liquidityAfter, sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    liquidity,
                    sqrtPriceX96,
                    int256(
                        amount0Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
                    ), // insurance0 + debt0
                    int256(amount1Unlocked) + amount1 // insurance1 + debt1
                );
        } else {
            amount0 = int256(uint256(position.debt0)); // debt in
            amount1 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out

            (liquidityAfter, sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    liquidity,
                    sqrtPriceX96,
                    int256(amount0Unlocked) + amount0, // insurance0 + debt0
                    int256(
                        amount1Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
                    ) // insurance1 + debt1
                );
        }

        // unadjusted for swap on oracle pool to repay debt to Marginal v1 pool
        amountOut = amount0 < 0
            ? uint256(-amount0)
            : (amount1 < 0 ? uint256(-amount1) : 0);

        // if token out is WETH9, liquidation rewards wrapped and used on oracle swap
        address tokenOut = !position.zeroForOne ? params.token0 : params.token1;
        if (tokenOut == WETH9) amountOut += position.rewards;

        // amount in is debt repaid pulled from oracle Uniswap v3 pool in exact output swap
        bool oracleZeroForOne = amount1 > 0;
        (int256 oracleAmount0, int256 oracleAmount1) = uniswapV3Quoter.quote(
            params.oracle,
            oracleZeroForOne,
            (oracleZeroForOne ? -amount1 : -amount0),
            (
                oracleZeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
        );

        uint256 oracleAmountIn = (
            oracleZeroForOne ? uint256(oracleAmount0) : uint256(oracleAmount1)
        );
        if (amountOut < oracleAmountIn) revert("IIA"); // Uniswap v3 pool error for not enough balance in on swap

        amountOut -= oracleAmountIn;
        if (amountOut < params.amountOutMinimum)
            revert("Amount out less than min");
    }

    /// @inheritdoc IQuoter
    function quoteExactInputSingle(
        IRouter.ExactInputSingleParams memory params
    )
        public
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        )
    {
        bool zeroForOne = params.tokenIn < params.tokenOut;
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: zeroForOne ? params.tokenIn : params.tokenOut,
                token1: zeroForOne ? params.tokenOut : params.tokenIn,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            uint8 feeProtocol,
            bool initialized
        ) = pool.state();
        if (!initialized) revert("Not initialized");

        uint160 sqrtPriceLimitX96 = params.sqrtPriceLimitX96 == 0
            ? (
                zeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
            : params.sqrtPriceLimitX96;

        if (
            params.amountIn == 0 || params.amountIn >= uint256(type(int256).max)
        ) revert("Invalid amountIn");
        int256 amountSpecified = int256(params.amountIn);

        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceLimitX96");

        int256 amountSpecifiedLessFee = amountSpecified -
            int256(
                SwapMath.swapFees(
                    uint256(amountSpecified),
                    PoolConstants.fee,
                    false
                )
            );
        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            liquidity,
            sqrtPriceX96,
            zeroForOne,
            amountSpecifiedLessFee
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert("sqrtPriceX96Next exceeds limit");

        // amounts without fees
        (int256 amount0, int256 amount1) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next
        );
        amountOut = uint256(-(zeroForOne ? amount1 : amount0));
        if (amountOut < params.amountOutMinimum) revert("Too little received");

        // account for protocol fees if turned on
        uint256 amountInLessFee = uint256(zeroForOne ? amount0 : amount1);
        uint256 fees = params.amountIn - amountInLessFee;
        uint256 amountIn = amountInLessFee + fees;
        if (feeProtocol > 0) amountIn -= uint256(fees / feeProtocol);

        // calculate liquidity, sqrtP after
        (liquidityAfter, sqrtPriceX96After) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                liquidity,
                sqrtPriceX96,
                zeroForOne ? int256(amountIn) : -int256(amountOut),
                zeroForOne ? -int256(amountOut) : int256(amountIn)
            );
    }

    /// @inheritdoc IQuoter
    function quoteExactInput(
        IRouter.ExactInputParams memory params
    )
        external
        view
        returns (
            uint256 amountOut,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        )
    {
        uint256 numPools = params.path.numPools();
        liquiditiesAfter = new uint128[](numPools);
        sqrtPricesX96After = new uint160[](numPools);

        uint256 i;
        while (true) {
            bool hasMultiplePools = params.path.hasMultiplePools();
            (
                address tokenIn,
                address tokenOut,
                uint24 maintenance,
                address oracle
            ) = params.path.decodeFirstPool();
            (
                params.amountIn,
                liquiditiesAfter[i],
                sqrtPricesX96After[i]
            ) = quoteExactInputSingle(
                IRouter.ExactInputSingleParams({
                    tokenIn: tokenIn,
                    tokenOut: tokenOut,
                    maintenance: maintenance,
                    oracle: oracle,
                    recipient: params.recipient, // irrelevant
                    deadline: params.deadline,
                    amountIn: params.amountIn,
                    amountOutMinimum: 0,
                    sqrtPriceLimitX96: 0
                })
            );
            i++; // for lists

            // exit out if reached end of path
            if (hasMultiplePools) {
                params.path = params.path.skipToken();
            } else {
                amountOut = params.amountIn;
                break;
            }
        }

        if (amountOut < params.amountOutMinimum) revert("Too little received");
    }

    /// @inheritdoc IQuoter
    function quoteExactOutputSingle(
        IRouter.ExactOutputSingleParams memory params
    )
        public
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        )
    {
        bool zeroForOne = params.tokenIn < params.tokenOut;
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: zeroForOne ? params.tokenIn : params.tokenOut,
                token1: zeroForOne ? params.tokenOut : params.tokenIn,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            uint8 feeProtocol,
            bool initialized
        ) = pool.state();
        if (!initialized) revert("Not initialized");

        uint160 sqrtPriceLimitX96 = params.sqrtPriceLimitX96 == 0
            ? (
                zeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
            : params.sqrtPriceLimitX96;

        if (
            params.amountOut == 0 ||
            params.amountOut >= uint256(type(int256).max)
        ) revert("Invalid amountOut");
        int256 amountSpecified = -int256(params.amountOut);

        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceLimitX96");

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            liquidity,
            sqrtPriceX96,
            zeroForOne,
            amountSpecified
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert("sqrtPriceX96Next exceeds limit");

        // amounts without fees
        (int256 amount0, int256 amount1) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next
        );
        uint256 amountOut = uint256(-amountSpecified);

        // account for protocol fees if turned on
        uint256 amountInLessFee = uint256(zeroForOne ? amount0 : amount1);
        uint256 fees = SwapMath.swapFees(
            amountInLessFee,
            PoolConstants.fee,
            true
        );
        amountIn = amountInLessFee + fees; // amount in required of swapper to send
        if (amountIn > params.amountInMaximum) revert("Too much requested");

        // account for protocol fees if turned on for amount in to pool
        uint256 amountInToPool = amountIn;
        if (feeProtocol > 0) amountInToPool -= uint256(fees / feeProtocol);

        // calculate liquidity, sqrtP after
        (liquidityAfter, sqrtPriceX96After) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                liquidity,
                sqrtPriceX96,
                zeroForOne ? int256(amountInToPool) : -int256(amountOut),
                zeroForOne ? -int256(amountOut) : int256(amountInToPool)
            );
    }

    /// @inheritdoc IQuoter
    function quoteExactOutput(
        IRouter.ExactOutputParams memory params
    )
        external
        view
        returns (
            uint256 amountIn,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        )
    {
        uint256 numPools = params.path.numPools();
        liquiditiesAfter = new uint128[](numPools);
        sqrtPricesX96After = new uint160[](numPools);

        uint256 i;
        while (true) {
            bool hasMultiplePools = params.path.hasMultiplePools();
            (
                address tokenOut,
                address tokenIn,
                uint24 maintenance,
                address oracle
            ) = params.path.decodeFirstPool();
            (
                params.amountOut,
                liquiditiesAfter[i],
                sqrtPricesX96After[i]
            ) = quoteExactOutputSingle(
                IRouter.ExactOutputSingleParams({
                    tokenIn: tokenIn,
                    tokenOut: tokenOut,
                    maintenance: maintenance,
                    oracle: oracle,
                    recipient: params.recipient, // irrelevant
                    deadline: params.deadline,
                    amountOut: params.amountOut,
                    amountInMaximum: type(uint256).max,
                    sqrtPriceLimitX96: 0
                })
            );
            i++; // for lists

            // exit out if reached end of path
            if (hasMultiplePools) {
                params.path = params.path.skipToken();
            } else {
                amountIn = params.amountOut;
                break;
            }
        }

        if (amountIn > params.amountInMaximum) revert("Too much requested");
    }

    /// @inheritdoc IQuoter
    function quoteAddLiquidity(
        IRouter.AddLiquidityParams memory params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 shares,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidityAfter
        )
    {
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            ,
            bool initialized
        ) = pool.state();
        if (!initialized) revert("Pool not initialized");

        uint128 liquidityDelta = LiquidityAmounts.getLiquidityForAmounts(
            sqrtPriceX96,
            params.amount0Desired,
            params.amount1Desired
        );
        if (liquidityDelta == 0) revert("Invalid liquidityDelta");

        // cache needed pool state
        uint256 totalSupply = pool.totalSupply();
        uint128 liquidityLocked = pool.liquidityLocked();

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            sqrtPriceX96
        );
        amount0 += 1;
        amount1 += 1;

        if (amount0 < params.amount0Min) revert("amount0 less than min");
        if (amount1 < params.amount1Min) revert("amount1 less than min");

        uint128 totalLiquidityAfter = liquidity +
            liquidityLocked +
            liquidityDelta;
        shares = totalSupply == 0
            ? totalLiquidityAfter
            : Math.mulDiv(
                totalSupply,
                liquidityDelta,
                totalLiquidityAfter - liquidityDelta
            );

        liquidityAfter = liquidity + liquidityDelta;
    }

    /// @inheritdoc IQuoter
    function quoteRemoveLiquidity(
        IRouter.RemoveLiquidityParams memory params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint128 liquidityDelta,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidityAfter
        )
    {
        IMarginalV1Pool pool = getPool(
            PoolAddress.PoolKey({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            ,
            bool initialized
        ) = pool.state();
        if (!initialized) revert("Not initialized");

        // cache needed pool state
        uint256 totalSupply = pool.totalSupply();
        uint128 liquidityLocked = pool.liquidityLocked();

        if (params.shares == 0 || params.shares > totalSupply)
            revert("Invalid shares");

        uint128 totalLiquidityBefore = liquidity + liquidityLocked;
        liquidityDelta = uint128(
            Math.mulDiv(totalLiquidityBefore, params.shares, totalSupply)
        );
        if (liquidityDelta > liquidity) revert("Invalid liquidityDelta");

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            sqrtPriceX96
        );
        if (amount0 < params.amount0Min) revert("amount0 less than min");
        if (amount1 < params.amount1Min) revert("amount1 less than min");

        liquidityAfter = liquidity - liquidityDelta;
    }
}
