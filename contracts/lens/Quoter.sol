// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {Position} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";
import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PositionAmounts} from "../libraries/PositionAmounts.sol";

import {INonfungiblePositionManager} from "../interfaces/INonfungiblePositionManager.sol";
import {IRouter} from "../interfaces/IRouter.sol";
import {IQuoter} from "../interfaces/IQuoter.sol";

contract Quoter is IQuoter, PeripheryImmutableState, PeripheryValidation {
    uint24 private constant fee = 1000;
    uint24 private constant reward = 50000;

    constructor(
        address _factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _WETH9) {}

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
            uint256 amountIn,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
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
            uint128 liquidity,
            uint160 sqrtPriceX96,
            ,
            ,
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
        if (liquidityDelta == 0 || liquidityDelta >= liquidity)
            revert("Invalid liquidityDelta");

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
        Position.Info memory position = Position.assemble(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            params.zeroForOne,
            0,
            0,
            0,
            0
        );
        if (
            position.size == 0 ||
            (params.zeroForOne ? position.debt0 == 0 : position.debt1 == 0)
        ) revert("Invalid position");

        uint128 marginMinimum = Position.marginMinimum(
            position,
            params.maintenance
        );
        if (marginMinimum == 0 || params.margin < marginMinimum)
            revert("Margin less than min");
        position.margin = params.margin;

        size = position.size;
        if (size < params.sizeMinimum) revert("Size less than min");

        debt = params.zeroForOne ? position.debt0 : position.debt1;
        if (debt > params.debtMaximum) revert("Debt greater than max");

        uint256 fees = Position.fees(position.size, fee);
        uint256 rewards = Position.liquidationRewards(position.size, reward);
        amountIn = params.margin + fees + rewards;

        // account for protocol fees *after* since taken from amountIn once transferred to pool
        if (feeProtocol > 0) fees -= uint256(fees / feeProtocol);

        (liquidityAfter, sqrtPriceX96After) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                !params.zeroForOne ? int256(fees) : int256(0),
                !params.zeroForOne ? int256(0) : int256(fees)
            );
    }

    /// @inheritdoc IQuoter
    function quoteExactInputSingle(
        IRouter.ExactInputSingleParams calldata params
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
            uint128 liquidity,
            uint160 sqrtPriceX96,
            ,
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
            int256(SwapMath.swapFees(uint256(amountSpecified), fee));
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
        IRouter.ExactInputParams calldata params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountOut,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        )
    {}

    /// @inheritdoc IQuoter
    function quoteExactOutputSingle(
        IRouter.ExactOutputSingleParams calldata params
    )
        public
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After
        )
    {}

    /// @inheritdoc IQuoter
    function quoteExactOutput(
        IRouter.ExactOutputParams calldata params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint128[] memory liquiditiesAfter,
            uint160[] memory sqrtPricesX96After
        )
    {}
}
