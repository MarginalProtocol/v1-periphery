// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * @title Router
 * @author Uniswap Labs
 *
 * @dev Fork of Uniswap V3 periphery SwapRouter for swaps and liquidity provision on Marginal V1 pools.
 */
pragma solidity =0.8.15;
pragma abicoder v2;

import {SafeCast} from "@uniswap/v3-core/contracts/libraries/SafeCast.sol";
import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {SelfPermit} from "@uniswap/v3-periphery/contracts/base/SelfPermit.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {IRouter} from "./interfaces/IRouter.sol";
import {LiquidityManagement} from "./base/LiquidityManagement.sol";
import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PoolInitializer} from "./base/PoolInitializer.sol";

import {CallbackValidation} from "./libraries/CallbackValidation.sol";
import {LiquidityAmounts} from "./libraries/LiquidityAmounts.sol";
import {Path} from "./libraries/Path.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";

contract Router is
    IRouter,
    PeripheryImmutableState,
    LiquidityManagement,
    PoolInitializer,
    PeripheryValidation,
    Multicall,
    SelfPermit
{
    using Path for bytes;
    using SafeCast for uint256;

    /// @dev Used as the placeholder value for amountInCached, because the computed amount in for an exact output swap
    /// can never actually be this value
    uint256 private constant DEFAULT_AMOUNT_IN_CACHED = type(uint256).max;

    /// @dev Transient storage variable used for returning the computed amount in for an exact output swap.
    uint256 private amountInCached = DEFAULT_AMOUNT_IN_CACHED;

    constructor(
        address _factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _WETH9) {}

    /// @dev Returns the pool for the given token pair, maintenance, and oracle. The pool contract may or may not exist.
    function getPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) private view returns (IMarginalV1Pool) {
        return
            IMarginalV1Pool(
                PoolAddress.getAddress(
                    factory,
                    PoolAddress.getPoolKey(tokenA, tokenB, maintenance, oracle)
                )
            );
    }

    struct SwapCallbackData {
        bytes path;
        address payer;
    }

    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata _data
    ) external override {
        require(amount0Delta > 0 || amount1Delta > 0); // swaps entirely within 0-liquidity regions are not supported
        SwapCallbackData memory data = abi.decode(_data, (SwapCallbackData));
        (
            address tokenIn,
            address tokenOut,
            uint24 maintenance,
            address oracle
        ) = data.path.decodeFirstPool();
        CallbackValidation.verifyCallback(
            factory,
            tokenIn,
            tokenOut,
            maintenance,
            oracle
        );

        (bool isExactInput, uint256 amountToPay) = amount0Delta > 0
            ? (tokenIn < tokenOut, uint256(amount0Delta))
            : (tokenOut < tokenIn, uint256(amount1Delta));
        if (isExactInput) {
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        } else {
            // either initiate the next swap or pay
            if (data.path.hasMultiplePools()) {
                data.path = data.path.skipToken();
                exactOutputInternal(amountToPay, msg.sender, 0, data);
            } else {
                amountInCached = amountToPay;
                tokenIn = tokenOut; // swap in/out because exact output swaps are reversed
                pay(tokenIn, data.payer, msg.sender, amountToPay);
            }
        }
    }

    /// @dev Performs a single exact input swap
    function exactInputInternal(
        uint256 amountIn,
        address recipient,
        uint160 sqrtPriceLimitX96,
        SwapCallbackData memory data
    ) private returns (uint256 amountOut) {
        // allow swapping to the router address with address 0
        if (recipient == address(0)) recipient = address(this);

        (
            address tokenIn,
            address tokenOut,
            uint24 maintenance,
            address oracle
        ) = data.path.decodeFirstPool();

        bool zeroForOne = tokenIn < tokenOut;

        (int256 amount0, int256 amount1) = getPool(
            tokenIn,
            tokenOut,
            maintenance,
            oracle
        ).swap(
                recipient,
                zeroForOne,
                amountIn.toInt256(),
                sqrtPriceLimitX96 == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : sqrtPriceLimitX96,
                abi.encode(data)
            );

        return uint256(-(zeroForOne ? amount1 : amount0));
    }

    /// @inheritdoc IRouter
    function exactInputSingle(
        ExactInputSingleParams calldata params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountOut)
    {
        amountOut = exactInputInternal(
            params.amountIn,
            params.recipient,
            params.sqrtPriceLimitX96,
            SwapCallbackData({
                path: abi.encodePacked(
                    params.tokenIn,
                    params.maintenance,
                    params.oracle,
                    params.tokenOut
                ),
                payer: msg.sender
            })
        );
        require(amountOut >= params.amountOutMinimum, "Too little received");
    }

    /// @inheritdoc IRouter
    function exactInput(
        ExactInputParams memory params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountOut)
    {
        address payer = msg.sender; // msg.sender pays for the first hop

        while (true) {
            bool hasMultiplePools = params.path.hasMultiplePools();

            // the outputs of prior swaps become the inputs to subsequent ones
            params.amountIn = exactInputInternal(
                params.amountIn,
                hasMultiplePools ? address(this) : params.recipient, // for intermediate swaps, this contract custodies
                0,
                SwapCallbackData({
                    path: params.path.getFirstPool(), // only the first pool in the path is necessary
                    payer: payer
                })
            );

            // decide whether to continue or terminate
            if (hasMultiplePools) {
                payer = address(this); // at this point, the caller has paid
                params.path = params.path.skipToken();
            } else {
                amountOut = params.amountIn;
                break;
            }
        }

        require(amountOut >= params.amountOutMinimum, "Too little received");
    }

    /// @dev Performs a single exact output swap
    function exactOutputInternal(
        uint256 amountOut,
        address recipient,
        uint160 sqrtPriceLimitX96,
        SwapCallbackData memory data
    ) private returns (uint256 amountIn) {
        // allow swapping to the router address with address 0
        if (recipient == address(0)) recipient = address(this);

        (
            address tokenOut,
            address tokenIn,
            uint24 maintenance,
            address oracle
        ) = data.path.decodeFirstPool();

        bool zeroForOne = tokenIn < tokenOut;

        (int256 amount0Delta, int256 amount1Delta) = getPool(
            tokenIn,
            tokenOut,
            maintenance,
            oracle
        ).swap(
                recipient,
                zeroForOne,
                -amountOut.toInt256(),
                sqrtPriceLimitX96 == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : sqrtPriceLimitX96,
                abi.encode(data)
            );

        uint256 amountOutReceived;
        (amountIn, amountOutReceived) = zeroForOne
            ? (uint256(amount0Delta), uint256(-amount1Delta))
            : (uint256(amount1Delta), uint256(-amount0Delta));
        // it's technically possible to not receive the full output amount,
        // so if no price limit has been specified, require this possibility away
        if (sqrtPriceLimitX96 == 0) require(amountOutReceived == amountOut);
    }

    /// @inheritdoc IRouter
    function exactOutputSingle(
        ExactOutputSingleParams calldata params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountIn)
    {
        // avoid an SLOAD by using the swap return data
        amountIn = exactOutputInternal(
            params.amountOut,
            params.recipient,
            params.sqrtPriceLimitX96,
            SwapCallbackData({
                path: abi.encodePacked(
                    params.tokenOut,
                    params.maintenance,
                    params.oracle,
                    params.tokenIn
                ),
                payer: msg.sender
            })
        );

        require(amountIn <= params.amountInMaximum, "Too much requested");
        // has to be reset even though we don't use it in the single hop case
        amountInCached = DEFAULT_AMOUNT_IN_CACHED;
    }

    /// @inheritdoc IRouter
    function exactOutput(
        ExactOutputParams calldata params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountIn)
    {
        // it's okay that the payer is fixed to msg.sender here, as they're only paying for the "final" exact output
        // swap, which happens first, and subsequent swaps are paid for within nested callback frames
        exactOutputInternal(
            params.amountOut,
            params.recipient,
            0,
            SwapCallbackData({path: params.path, payer: msg.sender})
        );

        amountIn = amountInCached;
        require(amountIn <= params.amountInMaximum, "Too much requested");
        amountInCached = DEFAULT_AMOUNT_IN_CACHED;
    }

    /// @inheritdoc IRouter
    function addLiquidity(
        AddLiquidityParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint256 shares, uint256 amount0, uint256 amount1)
    {
        (uint160 sqrtPriceX96, , , , , , , ) = getPool(
            params.token0,
            params.token1,
            params.maintenance,
            params.oracle
        ).state();
        uint128 liquidityDelta = LiquidityAmounts.getLiquidityForAmounts(
            sqrtPriceX96,
            params.amount0Desired,
            params.amount1Desired
        );

        (shares, amount0, amount1) = mint(
            MintParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: params.recipient,
                liquidityDelta: liquidityDelta,
                amount0Min: params.amount0Min,
                amount1Min: params.amount1Min
            })
        );
        emit IncreaseLiquidity(shares, liquidityDelta, amount0, amount1);
    }

    /// @inheritdoc IRouter
    function removeLiquidity(
        RemoveLiquidityParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1)
    {
        (liquidityDelta, amount0, amount1) = burn(
            BurnParams({
                token0: params.token0,
                token1: params.token1,
                maintenance: params.maintenance,
                oracle: params.oracle,
                recipient: params.recipient,
                shares: params.shares,
                amount0Min: params.amount0Min,
                amount1Min: params.amount1Min
            })
        );
        emit DecreaseLiquidity(params.shares, liquidityDelta, amount0, amount1);
    }
}
