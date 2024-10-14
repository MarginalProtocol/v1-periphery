// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {Position as PositionLibrary} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {OracleLibrary} from "@marginal/v1-core/contracts/libraries/OracleLibrary.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PoolConstants} from "../libraries/PoolConstants.sol";
import {PositionHealth} from "../libraries/PositionHealth.sol";

abstract contract PositionState {
    using PositionLibrary for PositionLibrary.Info;

    /// @notice Gets pool state synced for pool oracle updates
    /// @param pool The pool to get state of
    function getStateSynced(
        address pool
    )
        internal
        view
        returns (
            uint160 sqrtPriceX96,
            uint96 totalPositions,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint8 feeProtocol,
            bool initialized
        )
    {
        (
            sqrtPriceX96,
            totalPositions,
            liquidity,
            tick,
            blockTimestamp,
            tickCumulative,
            feeProtocol,
            initialized
        ) = IMarginalV1Pool(pool).state();

        // oracle update
        unchecked {
            tickCumulative +=
                int56(tick) *
                int56(uint56(uint32(block.timestamp) - blockTimestamp)); // overflow desired
            blockTimestamp = uint32(block.timestamp);
        }
    }

    /// @notice Gets external oracle tick cumulative values for time deltas: [secondsAgo, 0]
    /// @param pool The pool to get external oracle state for
    /// @param secondsAgo The seconds ago to average the oracle TWAP over to calculate position safety attributes
    function _getOracleSynced(
        address pool,
        uint32 secondsAgo
    ) internal view returns (int56[] memory oracleTickCumulatives) {
        address oracle = IMarginalV1Pool(pool).oracle();

        // zero seconds ago for oracle tickCumulative
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;

        (oracleTickCumulatives, ) = IUniswapV3Pool(oracle).observe(secondsAgos);
    }

    /// @notice Gets external oracle tick cumulative values for time deltas: [PoolConstants.secondsAgo, 0]
    /// @param pool The pool to get external oracle state for
    function getOracleSynced(
        address pool
    ) internal view returns (int56[] memory oracleTickCumulatives) {
        oracleTickCumulatives = _getOracleSynced(
            pool,
            PoolConstants.secondsAgo
        );
    }

    /// @notice Calculates the minimum margin requirement for the position to remain safe from liquidation
    /// @dev c_y (safe) >= (1+M) * d_x * max(P, TWAP) - s_y when zeroForOne = true when no funding
    /// or c_x (safe) >= (1+M) * d_y / min(P, TWAP) - s_x when zeroForOne = false when no funding
    /// @param info The synced position info
    /// @param marginMinimum The margin minimum when ignoring funding and liquidation
    /// @param maintenance The minimum maintenance margin requirement
    /// @param oracleTickCumulativeDelta The difference in oracle tick cumulatives averaged over to assess position safety with
    /// @param secondsAgo The seconds ago to average the oracle TWAP over to calculate position safety attributes
    function _safeMarginMinimum(
        PositionLibrary.Info memory info,
        uint128 marginMinimum,
        uint24 maintenance,
        int56 oracleTickCumulativeDelta,
        uint32 secondsAgo
    ) internal pure returns (uint128 safeMarginMinimum) {
        int24 positionTick = info.tick;
        int24 oracleTick = int24(
            oracleTickCumulativeDelta / int56(uint56(secondsAgo))
        );

        // change to using oracle tick for safe margin minimum calculation with liquidation and funding
        info.tick = oracleTick;
        safeMarginMinimum = info.marginMinimum(maintenance);
        if (marginMinimum > safeMarginMinimum)
            safeMarginMinimum = marginMinimum;

        info.tick = positionTick; // in case reuse info, return to actual position tick
    }

    /// @notice Gets pool position synced for funding updates using oracle TWAP averaged over `secondsAgo`
    /// @param pool The pool the position is on
    /// @param recipient The recipient of the position at open
    /// @param id The position id
    /// @param secondsAgo The seconds ago to average the oracle TWAP over to calculate position safety attributes
    function _getPositionSynced(
        address pool,
        address recipient,
        uint96 id,
        uint32 secondsAgo
    )
        internal
        view
        returns (
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            uint128 safeMarginMinimum,
            bool liquidated,
            bool safe,
            uint256 rewards,
            uint256 health
        )
    {
        PositionLibrary.Info memory info;
        {
            bytes32 key = keccak256(abi.encodePacked(recipient, id));

            uint128 _debt0;
            uint128 _debt1;
            int24 _tick;
            uint32 _blockTimestamp;
            int56 _tickCumulativeDelta;
            (
                size,
                _debt0,
                _debt1,
                ,
                ,
                zeroForOne,
                liquidated,
                _tick,
                _blockTimestamp,
                _tickCumulativeDelta,
                margin,
                ,
                rewards
            ) = IMarginalV1Pool(pool).positions(key);
            info = PositionLibrary.Info({
                size: size,
                debt0: _debt0,
                debt1: _debt1,
                insurance0: 0, // @dev irrelevant for sync
                insurance1: 0,
                zeroForOne: zeroForOne,
                liquidated: liquidated,
                tick: _tick,
                blockTimestamp: _blockTimestamp,
                tickCumulativeDelta: _tickCumulativeDelta,
                margin: margin,
                liquidityLocked: 0, // @dev irrelevant for sync
                rewards: rewards
            });
        }

        uint24 maintenance = IMarginalV1Pool(pool).maintenance();
        uint128 marginMinimum = info.marginMinimum(maintenance);
        uint160 oracleSqrtPriceX96;

        // sync if not settled or liquidated
        if (info.size > 0) {
            int56 oracleTickCumulativeDelta;
            {
                (
                    ,
                    ,
                    ,
                    ,
                    uint32 blockTimestampLast,
                    int56 tickCumulativeLast,
                    ,

                ) = getStateSynced(pool);

                int56[] memory oracleTickCumulativesLast = _getOracleSynced(
                    pool,
                    secondsAgo
                );
                oracleTickCumulativeDelta = OracleLibrary
                    .oracleTickCumulativeDelta(
                        oracleTickCumulativesLast[0],
                        oracleTickCumulativesLast[1]
                    );

                info.sync(
                    blockTimestampLast,
                    tickCumulativeLast,
                    oracleTickCumulativesLast[1], // zero seconds ago
                    PoolConstants.tickCumulativeRateMax,
                    PoolConstants.fundingPeriod
                );
            }

            oracleSqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
                oracleTickCumulativeDelta,
                secondsAgo
            );
            safe = info.safe(oracleSqrtPriceX96, maintenance);
            safeMarginMinimum = _safeMarginMinimum(
                info,
                marginMinimum,
                maintenance,
                oracleTickCumulativeDelta,
                secondsAgo
            );
        }

        debt = zeroForOne ? info.debt0 : info.debt1;
        health = oracleSqrtPriceX96 > 0
            ? PositionHealth.getHealthForPosition(
                zeroForOne,
                size,
                debt,
                margin,
                maintenance,
                oracleSqrtPriceX96
            )
            : 0;
    }

    /// @notice Gets pool position synced for funding updates
    /// @param pool The pool the position is on
    /// @param recipient The recipient of the position at open
    /// @param id The position id
    function getPositionSynced(
        address pool,
        address recipient,
        uint96 id
    )
        internal
        view
        returns (
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            uint128 safeMarginMinimum,
            bool liquidated,
            bool safe,
            uint256 rewards,
            uint256 health
        )
    {
        (
            zeroForOne,
            size,
            debt,
            margin,
            safeMarginMinimum,
            liquidated,
            safe,
            rewards,
            health
        ) = _getPositionSynced(pool, recipient, id, PoolConstants.secondsAgo);
    }
}
