// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {Position} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PositionAmounts} from "../libraries/PositionAmounts.sol";
import {INonfungiblePositionManager} from "../interfaces/INonfungiblePositionManager.sol";
import {IQuoter} from "../interfaces/IQuoter.sol";

contract Quoter is IQuoter, PeripheryImmutableState {
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
        if (!initialized) return (0, 0, 0, 0, 0);

        uint128 liquidityDelta = PositionAmounts.getLiquidityForSize(
            liquidity,
            sqrtPriceX96,
            params.maintenance,
            params.zeroForOne,
            params.sizeDesired
        );
        if (liquidityDelta == 0 || liquidityDelta >= liquidity)
            return (0, 0, 0, 0, 0);

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
        ) return (0, 0, 0, 0, 0);

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
        ) return (0, 0, 0, 0, 0);

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
        ) return (0, 0, 0, 0, 0);

        uint128 marginMinimum = Position.marginMinimum(
            position,
            params.maintenance
        );
        if (marginMinimum == 0 || params.margin < marginMinimum)
            return (0, 0, 0, 0, 0);
        position.margin = params.margin;

        size = position.size;
        debt = params.zeroForOne ? position.debt0 : position.debt1;

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
}
