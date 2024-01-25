// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3SwapCallback} from "@uniswap/v3-core/contracts/interfaces/callback/IUniswapV3SwapCallback.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {CallbackValidation as UniswapV3CallbackValidation} from "@uniswap/v3-periphery/contracts/libraries/CallbackValidation.sol";

import {IMarginalV1SwapCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SwapCallback.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";
import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PeripheryPayments} from "../base/PeripheryPayments.sol";

import {CallbackValidation} from "../libraries/CallbackValidation.sol";
import {Path} from "../libraries/Path.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";

/// @title PairAribtrageur
/// @notice Simple flash arbitrageur between Marginal v1 and their associated Uniswap v3 spot oracle pools
/// @dev WARNING: This contract is unaudited. Use at your own risk
contract PairArbitrageur is
    IMarginalV1SwapCallback,
    IUniswapV3SwapCallback,
    PeripheryImmutableState,
    PeripheryPayments,
    PeripheryValidation,
    Multicall
{
    /// @dev Used as the placeholder value for sqrtPriceLimit1X96
    uint160 private constant DEFAULT_SQRT_PRICE_LIMIT_X96_CACHED = 0;

    /// @dev Transient storage variable used for returning the computed amount in for an exact output swap.
    uint160 private sqrtPriceLimit1X96Cached =
        DEFAULT_SQRT_PRICE_LIMIT_X96_CACHED;

    error PoolNotInitialized();
    error PoolInvalid();
    error ArbitrageNotAvailable();
    error AmountOutLessThanMin(uint256 amountOut);

    constructor(
        address _factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _WETH9) {}

    struct SwapCallbackData {
        bytes path;
        address payer;
    }

    /// @inheritdoc IMarginalV1SwapCallback
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
        ) = Path.decodeFirstPool(data.path);
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

        if (!isExactInput) {
            // token combos for next swap
            address tokenIn_ = tokenIn;
            address tokenOut_ = tokenOut;

            // swap in/out because exact output swaps are reversed
            tokenIn = tokenOut_;
            tokenOut = tokenIn_;

            // swap on Uniswap for second swap if this is exactOutput (since first swap)
            // amount specified on second pool swap is exactInput
            bool zeroForOne = amount0Delta < 0; // sending token0 pulled from marginal in to uniswap
            int256 amountSpecified = zeroForOne ? -amount0Delta : -amount1Delta;

            uint24 uniswapV3Fee = IUniswapV3Pool(oracle).fee();
            SwapCallbackData memory data_ = SwapCallbackData({
                path: abi.encodePacked(
                    tokenIn_, // tokenIn
                    uniswapV3Fee, // fee; bit of a hack on uint24 for uni callback validation
                    msg.sender, // pool; bit of a hack on address for uni callback validation
                    tokenOut_ // tokenOut
                ),
                payer: data.payer
            });
            IUniswapV3Pool(oracle).swap(
                data.payer,
                zeroForOne,
                amountSpecified,
                sqrtPriceLimit1X96Cached == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : sqrtPriceLimit1X96Cached,
                abi.encode(data_)
            );
            // pay Marginal pool for what is still owed
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        } else {
            // otherwise this is second swap and simply need to pay marginal pool
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        }
    }

    /// @inheritdoc IUniswapV3SwapCallback
    function uniswapV3SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata _data
    ) external override {
        require(amount0Delta > 0 || amount1Delta > 0); // swaps entirely within 0-liquidity regions are not supported
        SwapCallbackData memory data = abi.decode(_data, (SwapCallbackData));
        (
            address tokenIn,
            address tokenOut,
            uint24 uniswapV3Fee,
            address pool
        ) = Path.decodeFirstPool(data.path);
        if (!PoolAddress.isPool(factory, pool)) revert PoolInvalid();
        UniswapV3CallbackValidation.verifyCallback(
            uniswapV3Factory,
            tokenIn,
            tokenOut,
            uniswapV3Fee
        );

        (bool isExactInput, uint256 amountToPay) = amount0Delta > 0
            ? (tokenIn < tokenOut, uint256(amount0Delta))
            : (tokenOut < tokenIn, uint256(amount1Delta));

        if (!isExactInput) {
            // token combos for next swap
            address tokenIn_ = tokenIn;
            address tokenOut_ = tokenOut;

            // swap in/out because exact output swaps are reversed
            tokenIn = tokenOut_;
            tokenOut = tokenIn_;

            // swap on Marginal for second swap if this is exactOutput (since first swap)
            // amount specified on second pool swap is exactInput
            bool zeroForOne = amount0Delta < 0; // sending token0 pulled from marginal in to uniswap
            int256 amountSpecified = zeroForOne ? -amount0Delta : -amount1Delta;

            uint24 maintenance = IMarginalV1Pool(pool).maintenance();
            SwapCallbackData memory data_ = SwapCallbackData({
                path: abi.encodePacked(
                    tokenIn_, // tokenIn
                    maintenance, // maintenance
                    msg.sender, // oracle
                    tokenOut_ // tokenOut
                ),
                payer: data.payer
            });
            IMarginalV1Pool(pool).swap(
                data.payer,
                zeroForOne,
                amountSpecified,
                sqrtPriceLimit1X96Cached == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : sqrtPriceLimit1X96Cached,
                abi.encode(data_)
            );
            // pay Marginal pool for what is still owed
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        } else {
            // otherwise this is second swap and simply need to pay marginal pool
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        }
    }

    struct ExecuteParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        address tokenOut;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimit0X96; // limit on first pool swap
        uint160 sqrtPriceLimit1X96; // limit on second pool swap
        uint256 deadline;
    }

    /// @notice Executes the arb between Marginal v1 pool and its associated Uniswap v3 oracle
    /// @dev Naively assumes x*y=L^2 for both pools, so works for swaps within a tick on Uniswap v3.
    /// Also ignores fees in calculation for size to arb with.
    function execute(
        ExecuteParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (uint256 amountOut)
    {
        require(params.token0 < params.token1);
        require(
            params.tokenOut == params.token0 || params.tokenOut == params.token1
        );
        address pool = PoolAddress.getAddress(
            factory,
            PoolAddress.getPoolKey(
                params.token0,
                params.token1,
                params.maintenance,
                params.oracle
            )
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
        ) = IMarginalV1Pool(pool).state();
        if (!initialized) revert PoolNotInitialized();
        (uint160 oracleSqrtPriceX96, , , , , , ) = IUniswapV3Pool(params.oracle)
            .slot0();
        uint128 oracleLiquidity = IUniswapV3Pool(params.oracle).liquidity();

        // for access in callback
        sqrtPriceLimit1X96Cached = params.sqrtPriceLimit1X96;

        // del y = ((L0 * L1) / (L0 + L1)) * (sqrtPrice1X96 - sqrtPrice0X96) is y amount to add to (> 0) or take out of (< 0)
        // or del x = ((L0 * L1) / (L0 + L1)) * (1 / sqrtPrice1X96 - 1 / sqrtPrice0X96) is x amount to add to (> 0) or take out of (< 0)
        // first pool and send to second pool for prices to align post arbitrage. Ignores fees and assumes x*y = L^2 for both pools
        if (sqrtPriceX96 == oracleSqrtPriceX96) revert ArbitrageNotAvailable();
        if (
            (sqrtPriceX96 > oracleSqrtPriceX96 &&
                params.tokenOut == params.token0) ||
            (sqrtPriceX96 < oracleSqrtPriceX96 &&
                params.tokenOut == params.token1)
        ) {
            // swap on marginal first then uniswap second
            bool zeroForOne = sqrtPriceX96 > oracleSqrtPriceX96; // zeroForOne on Marginal v1 pool
            uint256 prod = (uint256(liquidity) * uint256(oracleLiquidity)) /
                (uint256(liquidity) + uint256(oracleLiquidity)); // no overflow since uint128 for liquidity
            int256 amountSpecified = zeroForOne
                ? -int256(
                    Math.mulDiv(
                        prod,
                        sqrtPriceX96 - oracleSqrtPriceX96,
                        FixedPoint96.Q96
                    )
                )
                : -int256(
                    (prod << FixedPoint96.RESOLUTION) /
                        sqrtPriceX96 -
                        (prod << FixedPoint96.RESOLUTION) /
                        oracleSqrtPriceX96
                );

            // amount specified on first pool swap is exactOutput
            // second swap on Uniswap occurs in IMarginalV1SwapCallback
            SwapCallbackData memory data = SwapCallbackData({
                path: abi.encodePacked(
                    zeroForOne ? params.token1 : params.token0, // tokenOut
                    params.maintenance,
                    params.oracle,
                    zeroForOne ? params.token0 : params.token1 // tokenIn
                ),
                payer: address(this)
            });
            IMarginalV1Pool(pool).swap(
                address(this),
                zeroForOne,
                amountSpecified,
                params.sqrtPriceLimit0X96 == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : params.sqrtPriceLimit0X96,
                abi.encode(data)
            );
        } else {
            // swap on uniswap first then marginal second
            bool zeroForOne = oracleSqrtPriceX96 > sqrtPriceX96; // zeroForOne on Uniswap v3 pool
            uint256 prod = (uint256(liquidity) * uint256(oracleLiquidity)) /
                (uint256(liquidity) + uint256(oracleLiquidity)); // no overflow since uint128 for liquidity
            int256 amountSpecified = zeroForOne
                ? -int256(
                    Math.mulDiv(
                        prod,
                        oracleSqrtPriceX96 - sqrtPriceX96,
                        FixedPoint96.Q96
                    )
                )
                : -int256(
                    (prod << FixedPoint96.RESOLUTION) /
                        oracleSqrtPriceX96 -
                        (prod << FixedPoint96.RESOLUTION) /
                        sqrtPriceX96
                );

            // amount specified on first pool swap is exactOutput
            // second swap on Marginal occurs in IUniswapV3SwapCallback
            uint24 uniswapV3Fee = IUniswapV3Pool(params.oracle).fee();
            SwapCallbackData memory data = SwapCallbackData({
                path: abi.encodePacked(
                    zeroForOne ? params.token1 : params.token0, // tokenOut
                    uniswapV3Fee, // bit of a hack to use fee here
                    pool, // bit of a hack to use Marginal v1 pool here
                    zeroForOne ? params.token0 : params.token1 // tokenIn
                ),
                payer: address(this)
            });
            IUniswapV3Pool(params.oracle).swap(
                address(this),
                zeroForOne,
                amountSpecified,
                params.sqrtPriceLimit0X96 == 0
                    ? (
                        zeroForOne
                            ? TickMath.MIN_SQRT_RATIO + 1
                            : TickMath.MAX_SQRT_RATIO - 1
                    )
                    : params.sqrtPriceLimit0X96,
                abi.encode(data)
            );
        }

        // reset for next call to execute
        sqrtPriceLimit1X96Cached = DEFAULT_SQRT_PRICE_LIMIT_X96_CACHED;

        // send profits to recipient
        amountOut = balance(params.tokenOut);
        if (amountOut < params.amountOutMinimum)
            revert AmountOutLessThanMin(amountOut);
        pay(params.tokenOut, address(this), params.recipient, amountOut);
    }
}
