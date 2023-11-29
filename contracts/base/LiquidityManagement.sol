// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IMarginalV1MintCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {PeripheryPayments} from "./PeripheryPayments.sol";
import {CallbackValidation} from "../libraries/CallbackValidation.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";

abstract contract LiquidityManagement is
    IMarginalV1MintCallback,
    PeripheryImmutableState,
    PeripheryPayments
{
    struct LiquidityCallbackData {
        PoolAddress.PoolKey poolKey;
        address payer;
    }

    error Amount0LessThanMin(uint256 amount0);
    error Amount1LessThanMin(uint256 amount1);

    /// @dev Returns the pool for the given token pair and maintenance. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool) {
        return IMarginalV1Pool(PoolAddress.getAddress(factory, poolKey));
    }

    struct MintParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint128 liquidityDelta;
        uint256 amount0Min;
        uint256 amount1Min;
    }

    /// @notice Mints liquidity on pool
    function mint(
        MintParams memory params
    )
        internal
        virtual
        returns (uint256 shares, uint256 amount0, uint256 amount1)
    {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        (shares, amount0, amount1) = pool.mint(
            params.recipient,
            params.liquidityDelta,
            abi.encode(
                LiquidityCallbackData({poolKey: poolKey, payer: msg.sender})
            )
        );

        if (amount0 < params.amount0Min) revert Amount0LessThanMin(amount0);
        if (amount1 < params.amount1Min) revert Amount1LessThanMin(amount1);
    }

    /// @inheritdoc IMarginalV1MintCallback
    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external virtual {
        LiquidityCallbackData memory decoded = abi.decode(
            data,
            (LiquidityCallbackData)
        );
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    struct BurnParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        address recipient;
        uint256 shares;
        uint256 amount0Min;
        uint256 amount1Min;
    }

    /// @notice Burns liquidity on pool
    function burn(
        BurnParams memory params
    )
        internal
        virtual
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1)
    {
        PoolAddress.PoolKey memory poolKey = PoolAddress.PoolKey({
            token0: params.token0,
            token1: params.token1,
            maintenance: params.maintenance,
            oracle: params.oracle
        });
        IMarginalV1Pool pool = getPool(poolKey);

        if (params.shares > 0)
            pay(address(pool), msg.sender, address(this), params.shares);

        (liquidityDelta, amount0, amount1) = pool.burn(
            params.recipient,
            params.shares
        );

        if (amount0 < params.amount0Min) revert Amount0LessThanMin(amount0);
        if (amount1 < params.amount1Min) revert Amount1LessThanMin(amount1);
    }
}
