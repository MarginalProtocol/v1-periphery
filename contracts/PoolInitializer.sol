// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";

import {IMarginalV1SwapCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SwapCallback.sol";
import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";

import {LiquidityManagement} from "./base/LiquidityManagement.sol";
import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";

import {CallbackValidation} from "./libraries/CallbackValidation.sol";
import {LiquidityAmounts} from "./libraries/LiquidityAmounts.sol";
import {Path} from "./libraries/Path.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";
import {PoolConstants} from "./libraries/PoolConstants.sol";

import {IPoolInitializer} from "./interfaces/IPoolInitializer.sol";

/// @title Initializer for Marginal v1 pools
/// @notice Provides methods for preparing, creating and initializing a Marginal v1 pool and its associated Uniswap v3 oracle
contract PoolInitializer is
    IPoolInitializer,
    IMarginalV1SwapCallback,
    PeripheryImmutableState,
    LiquidityManagement,
    PeripheryValidation,
    Multicall
{
    using Path for bytes;

    event PoolInitialize(
        address indexed sender,
        address pool,
        uint256 shares,
        int256 amount0,
        int256 amount1
    );

    error InvalidOracle();
    error PoolNotInitialized();
    error AmountInGreaterThanMax(uint256 amountIn);
    error AmountOutLessThanMin(uint256 amountOut);
    error LiquidityBurnedLessThanMin();
    error Amount0BurnedGreaterThanMax(int256 amount0Burned);
    error Amount1BurnedGreaterThanMax(int256 amount1Burned);

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
        require(isExactInput);
        pay(tokenIn, data.payer, msg.sender, amountToPay);
    }

    /// @inheritdoc IPoolInitializer
    function createAndInitializePoolIfNecessary(
        CreateAndInitializeParams calldata params
    )
        public
        payable
        override
        checkDeadline(params.deadline)
        returns (address pool, uint256 shares, int256 amount0, int256 amount1)
    {
        require(params.token0 < params.token1);
        address oracle = IUniswapV3Factory(uniswapV3Factory).getPool(
            params.token0,
            params.token1,
            params.uniswapV3Fee
        );
        if (oracle == address(0)) revert InvalidOracle();

        pool = IMarginalV1Factory(factory).getPool(
            params.token0,
            params.token1,
            params.maintenance,
            oracle
        );
        if (pool == address(0)) {
            pool = IMarginalV1Factory(factory).createPool(
                params.token0,
                params.token1,
                params.maintenance,
                params.uniswapV3Fee
            );
        }

        // if not initialized, mint min liquidity with dust then swap to given price before adding full amount of liquidity
        (, , , , , , , bool initialized) = IMarginalV1Pool(pool).state();
        if (!initialized) {
            if (params.liquidityBurned <= PoolConstants.MINIMUM_LIQUIDITY)
                revert LiquidityBurnedLessThanMin();
            (, uint256 amount0BurnedOnMint, uint256 amount1BurnedOnMint) = mint(
                MintParams({
                    token0: params.token0,
                    token1: params.token1,
                    maintenance: params.maintenance,
                    oracle: oracle,
                    recipient: pool,
                    liquidityDelta: params.liquidityBurned, // burn extra to pool in case need buffer on rounding for swap (amountDelta > 0)
                    amount0Min: 0,
                    amount1Min: 0
                })
            );

            (
                int256 amount0BurnedOnSwap,
                int256 amount1BurnedOnSwap
            ) = initializePoolSqrtPriceX96(
                    InitializePoolSqrtPriceX96Params({
                        token0: params.token0,
                        token1: params.token1,
                        maintenance: params.maintenance,
                        oracle: oracle,
                        recipient: msg.sender,
                        sqrtPriceX96: params.sqrtPriceX96,
                        amountInMaximum: type(uint256).max, // impose max on amounts burned (including swap) below
                        amountOutMinimum: 0, // impose min on amounts in liquidity added in mint call below
                        sqrtPriceLimitX96: params.sqrtPriceLimitX96,
                        deadline: params.deadline
                    })
                );

            // check haven't burned more than want
            int256 amount0Burned = int256(amount0BurnedOnMint) +
                amount0BurnedOnSwap;
            if (amount0Burned > params.amount0BurnedMax)
                revert Amount0BurnedGreaterThanMax(amount0Burned);
            int256 amount1Burned = int256(amount1BurnedOnMint) +
                amount1BurnedOnSwap;
            if (amount1Burned > params.amount1BurnedMax)
                revert Amount1BurnedGreaterThanMax(amount1Burned);

            uint128 liquidityDelta = LiquidityAmounts.getLiquidityForAmounts(
                params.sqrtPriceX96,
                params.amount0Desired,
                params.amount1Desired
            );

            uint256 _amount0;
            uint256 _amount1;
            (shares, _amount0, _amount1) = mint(
                MintParams({
                    token0: params.token0,
                    token1: params.token1,
                    maintenance: params.maintenance,
                    oracle: oracle,
                    recipient: params.recipient,
                    liquidityDelta: liquidityDelta,
                    amount0Min: params.amount0Min,
                    amount1Min: params.amount1Min
                })
            );

            amount0 = int256(_amount0) + amount0Burned;
            amount1 = int256(_amount1) + amount1Burned;

            // any remaining ETH in the contract from payable return to sender
            refundETH();

            emit PoolInitialize(msg.sender, pool, shares, amount0, amount1);
        }
    }

    /// @inheritdoc IPoolInitializer
    function initializePoolSqrtPriceX96(
        InitializePoolSqrtPriceX96Params memory params
    )
        public
        payable
        override
        checkDeadline(params.deadline)
        returns (int256 amount0, int256 amount1)
    {
        require(params.token0 < params.token1);
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
            uint160 sqrtPriceX96Existing,
            ,
            uint128 liquidityExisting,
            ,
            ,
            ,
            ,
            bool initialized
        ) = IMarginalV1Pool(pool).state();
        if (!initialized) revert PoolNotInitialized();

        // calculate amount in needed (including fees) to get pool price to sqrtPriceX96 desired
        // @dev ignores fee add to liquidity effect on price for simplicity
        (int256 amount0Delta, int256 amount1Delta) = SwapMath.swapAmounts(
            liquidityExisting,
            sqrtPriceX96Existing,
            params.sqrtPriceX96
        );
        bool zeroForOne = params.sqrtPriceX96 < sqrtPriceX96Existing;
        int256 amountSpecified = zeroForOne ? amount0Delta : amount1Delta;
        require(amountSpecified > 0);
        amountSpecified += int256(
            SwapMath.swapFees(uint256(amountSpecified), PoolConstants.fee, true)
        );

        uint256 amountInMaximum = params.amountInMaximum == 0
            ? type(uint256).max
            : params.amountInMaximum;
        if (uint256(amountSpecified) > amountInMaximum)
            revert AmountInGreaterThanMax(uint256(amountSpecified));

        SwapCallbackData memory data = SwapCallbackData({
            path: abi.encodePacked(
                zeroForOne ? params.token0 : params.token1, // tokenIn
                params.maintenance,
                params.oracle,
                zeroForOne ? params.token1 : params.token0 // tokenOut
            ),
            payer: msg.sender
        });

        (amount0, amount1) = IMarginalV1Pool(pool).swap(
            params.recipient,
            zeroForOne,
            amountSpecified,
            params.sqrtPriceLimitX96 == 0
                ? (
                    zeroForOne
                        ? TickMath.MIN_SQRT_RATIO + 1
                        : TickMath.MAX_SQRT_RATIO - 1
                )
                : params.sqrtPriceLimitX96,
            abi.encode(data)
        );
        uint256 amountOut = uint256(-(zeroForOne ? amount1 : amount0));
        if (amountOut < params.amountOutMinimum)
            revert AmountOutLessThanMin(amountOut);
    }

    /// @inheritdoc IPoolInitializer
    function initializeOracleIfNecessary(
        InitializeOracleParams calldata params
    ) external override {
        require(params.token0 < params.token1);
        address oracle = IUniswapV3Factory(uniswapV3Factory).getPool(
            params.token0,
            params.token1,
            params.uniswapV3Fee
        );
        if (oracle == address(0)) revert InvalidOracle();

        (
            ,
            ,
            ,
            ,
            uint16 observationCardinalityNextExisting,
            ,

        ) = IUniswapV3Pool(oracle).slot0();
        uint16 observationCardinalityMinimum = IMarginalV1Factory(factory)
            .observationCardinalityMinimum();
        require(
            observationCardinalityNextExisting <
                params.observationCardinalityNext &&
                observationCardinalityMinimum <=
                params.observationCardinalityNext
        );

        if (
            observationCardinalityNextExisting < observationCardinalityMinimum
        ) {
            IUniswapV3Pool(oracle).increaseObservationCardinalityNext(
                params.observationCardinalityNext
            );
        }
    }
}
