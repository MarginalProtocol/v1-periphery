// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3SwapCallback} from "@uniswap/v3-core/contracts/interfaces/callback/IUniswapV3SwapCallback.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {IMarginalV1AdjustCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1OpenCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";
import {Position as PositionLibrary} from "@marginal/v1-core/contracts/libraries/Position.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {PeripheryPayments} from "./PeripheryPayments.sol";
import {CallbackValidation} from "../libraries/CallbackValidation.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

abstract contract PositionManagement is
    IMarginalV1AdjustCallback,
    IMarginalV1OpenCallback,
    IMarginalV1SettleCallback,
    IUniswapV3SwapCallback,
    PeripheryImmutableState,
    PeripheryPayments
{
    struct PositionCallbackData {
        PoolAddress.PoolKey poolKey;
        address payer;
    }

    error SizeLessThanMin(uint256 size);
    error DebtGreaterThanMax(uint256 debt);
    error AmountInGreaterThanMax(uint256 amountIn);
    error AmountOutLessThanMin(uint256 amountOut);
    error RewardsLessThanMin(uint256 rewardsMinimum);

    /// @dev Returns the pool for the given token pair and maintenance. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool) {
        return IMarginalV1Pool(PoolAddress.getAddress(factory, poolKey));
    }

    struct OpenParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        bool zeroForOne;
        uint128 liquidityDelta;
        uint160 sqrtPriceLimitX96;
        uint128 margin;
        uint128 sizeMinimum;
        uint128 debtMaximum;
        uint256 amountInMaximum;
    }

    /// @notice Opens a new position on pool
    function open(
        OpenParams memory params
    )
        internal
        virtual
        returns (
            uint256 id,
            uint256 size,
            uint256 debt,
            uint256 margin,
            uint256 fees,
            uint256 rewards
        )
    {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        rewards = PositionLibrary.liquidationRewards(
            block.basefee,
            PoolConstants.blockBaseFeeMin,
            PoolConstants.gasLiquidate,
            PoolConstants.rewardPremium
        ); // deposited for liquidation reward escrow
        // @dev use address(this).balance and not msg.value to avoid issues with multicall
        if (address(this).balance < rewards) revert RewardsLessThanMin(rewards); // only send the min required

        uint256 amount0;
        uint256 amount1;
        (id, size, debt, amount0, amount1) = pool.open{value: rewards}(
            params.recipient,
            params.zeroForOne,
            params.liquidityDelta,
            params.sqrtPriceLimitX96,
            params.margin,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
        if (size < uint256(params.sizeMinimum)) revert SizeLessThanMin(size);
        if (debt > uint256(params.debtMaximum)) revert DebtGreaterThanMax(debt);

        uint256 amountIn = (!params.zeroForOne) ? amount0 : amount1; // in margin token
        if (amountIn > params.amountInMaximum)
            revert AmountInGreaterThanMax(amountIn);

        margin = params.margin;
        fees = amountIn - margin;
    }

    /// @inheritdoc IMarginalV1OpenCallback
    function marginalV1OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external virtual {
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    struct AdjustParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint96 id;
        int128 marginDelta;
    }

    /// @notice Adjusts margin backing position on pool
    function adjust(
        AdjustParams memory params
    ) internal virtual returns (uint256 margin0, uint256 margin1) {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        (margin0, margin1) = pool.adjust(
            params.recipient,
            params.id,
            params.marginDelta,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
    }

    /// @inheritdoc IMarginalV1AdjustCallback
    function marginalV1AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external virtual {
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    struct SettleParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint96 id;
    }

    /// @notice Settles a position on pool via external payer of debt
    function settle(
        SettleParams memory params
    )
        internal
        virtual
        returns (int256 amount0, int256 amount1, uint256 rewards)
    {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        (amount0, amount1, rewards) = pool.settle(
            params.recipient,
            params.id,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
    }

    struct FlashParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint96 id;
        uint256 amountOutMinimum;
    }

    /// @notice Settles a position by repaying debt with portion of size swapped through spot
    function flash(
        FlashParams memory params
    ) internal virtual returns (uint256 amountOut, uint256 rewards) {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        address payer = address(this);
        int256 amount0;
        int256 amount1;
        (amount0, amount1, rewards) = pool.settle(
            payer,
            params.id,
            abi.encode(PositionCallbackData({poolKey: poolKey, payer: payer}))
        );

        address tokenOut = amount0 < 0 ? params.token0 : params.token1;
        amountOut = balance(tokenOut);

        if (amountOut < params.amountOutMinimum)
            revert AmountOutLessThanMin(amountOut);
        if (amountOut > 0) pay(tokenOut, payer, params.recipient, amountOut);
    }

    /// @inheritdoc IMarginalV1SettleCallback
    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external virtual {
        if (amount0Delta <= 0 && amount1Delta <= 0) revert SizeLessThanMin(0); // can't settle position with zero size; Q: ok? necessary?
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        if (decoded.payer == address(this)) {
            // swap portion of flashed size through spot to repay debt
            bool zeroForOne = amount1Delta > 0; // owe 1 to marginal if true
            IUniswapV3Pool(decoded.poolKey.oracle).swap(
                msg.sender,
                zeroForOne,
                (zeroForOne ? -amount1Delta : -amount0Delta),
                (
                    zeroForOne
                        ? TickMath.MIN_SQRT_RATIO + 1
                        : TickMath.MAX_SQRT_RATIO - 1
                ),
                abi.encode(decoded.poolKey)
            );
        } else {
            // simply pay debt from external payer
            if (amount0Delta > 0)
                pay(
                    decoded.poolKey.token0,
                    decoded.payer,
                    msg.sender,
                    uint256(amount0Delta)
                );
            if (amount1Delta > 0)
                pay(
                    decoded.poolKey.token1,
                    decoded.payer,
                    msg.sender,
                    uint256(amount1Delta)
                );
        }
    }

    /// @inheritdoc IUniswapV3SwapCallback
    function uniswapV3SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external virtual {
        require(amount0Delta > 0 || amount1Delta > 0); // swaps entirely within 0-liquidity regions are not supported
        PoolAddress.PoolKey memory poolKey = abi.decode(
            data,
            (PoolAddress.PoolKey)
        );
        CallbackValidation.verifyUniswapV3Callback(factory, poolKey);

        if (amount0Delta > 0)
            pay(
                poolKey.token0,
                address(this),
                msg.sender,
                uint256(amount0Delta)
            );
        if (amount1Delta > 0)
            pay(
                poolKey.token1,
                address(this),
                msg.sender,
                uint256(amount1Delta)
            );
    }

    struct LiquidateParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        address owner;
        uint96 id;
    }

    /// @notice Liquidates a position on pool
    function liquidate(
        LiquidateParams memory params
    ) internal virtual returns (uint256 rewards) {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        rewards = pool.liquidate(params.recipient, params.owner, params.id);
    }
}
