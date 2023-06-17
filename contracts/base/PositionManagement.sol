// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity =0.8.15;

import {IMarginalV1AdjustCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1OpenCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {PeripheryPayments} from "./PeripheryPayments.sol";
import {CallbackValidation} from "../libraries/CallbackValidation.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";

abstract contract PositionManagement is
    IMarginalV1AdjustCallback,
    IMarginalV1OpenCallback,
    IMarginalV1SettleCallback,
    PeripheryImmutableState,
    PeripheryPayments
{
    struct PositionCallbackData {
        PoolAddress.PoolKey poolKey;
        address payer;
    }
    struct AdjustPositionParams {
        address token0;
        address token1;
        uint24 maintenance;
        address recipient;
        uint104 id;
        int128 marginDelta;
    }
    struct OpenPositionParams {
        address token0;
        address token1;
        uint24 maintenance;
        address recipient;
        bool zeroForOne;
        uint128 liquidityDelta;
        uint160 sqrtPriceLimitX96;
        uint128 margin;
        uint256 sizeMinimum;
    }
    struct SettlePositionParams {
        address token0;
        address token1;
        uint24 maintenance;
        address recipient;
        uint104 id;
    }

    error SizeLessThanMin(uint256 size);

    /// @dev Returns the pool for the given token pair and maintenance. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) private view returns (IMarginalV1Pool) {
        return
            IMarginalV1Pool(
                PoolAddress.computeAddress(deployer, factory, poolKey)
            );
    }

    /// @notice Opens a new position on pool
    // TODO: test
    function openPosition(
        OpenPositionParams memory params
    ) internal returns (uint256 id, uint256 size, IMarginalV1Pool pool) {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance
        });
        pool = getPool(poolKey);

        (id, size) = pool.open(
            params.recipient,
            params.zeroForOne,
            params.liquidityDelta,
            params.sqrtPriceLimitX96,
            params.margin,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
        if (size < params.sizeMinimum) revert SizeLessThanMin(size);
    }

    function marginalV1OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(deployer, factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    /// @notice Adjusts margin backing position on pool
    // TODO: test
    function adjustPosition(
        AdjustPositionParams memory params
    )
        internal
        returns (uint256 margin0, uint256 margin1, IMarginalV1Pool pool)
    {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance
        });
        pool = getPool(poolKey);

        (margin0, margin1) = pool.adjust(
            params.recipient,
            params.id,
            params.marginDelta,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
    }

    function marginalV1AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(deployer, factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    /// @notice Settles a position on pool
    // TODO: test
    function settlePosition(
        SettlePositionParams memory params
    ) internal returns (int256 amount0, int256 amount1, IMarginalV1Pool pool) {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance
        });
        pool = getPool(poolKey);

        (amount0, amount1) = pool.settle(
            params.recipient,
            params.id,
            abi.encode(
                PositionCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );
    }

    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        if (amount0Delta <= 0 && amount1Delta <= 0) revert SizeLessThanMin(0); // can't settle position with zero size; Q: ok? necessary?
        PositionCallbackData memory decoded = abi.decode(
            data,
            (PositionCallbackData)
        );
        CallbackValidation.verifyCallback(deployer, factory, decoded.poolKey);

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
