// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {Position as PositionLibrary} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

abstract contract PositionState {
    using PositionLibrary for PositionLibrary.Info;

    uint24 private constant tickCumulativeRateMax = 920; // bound on funding rate of ~10% per funding period
    uint32 private constant secondsAgo = 43200; // 12 hr TWAP for oracle price
    uint32 private constant fundingPeriod = 604800; // 7 day funding period

    /// @notice Gets pool state synced for pool oracle updates
    /// @param pool The pool to get state of
    function getStateSynced(
        address pool
    )
        internal
        view
        returns (
            uint128 liquidity,
            uint160 sqrtPriceX96,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint96 totalPositions,
            uint8 feeProtocol,
            bool initialized
        )
    {
        (
            liquidity,
            sqrtPriceX96,
            tick,
            blockTimestamp,
            tickCumulative,
            totalPositions,
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

    /// @notice Gets external oracle last tick cumulative
    /// @param pool The pool to get external oracle state for
    function getOracleSynced(
        address pool
    ) internal view returns (int56 oracleTickCumulative) {
        address oracle = IMarginalV1Pool(pool).oracle();

        // zero seconds ago for oracle tickCumulative
        uint32[] memory secondsAgos = new uint32[](1);
        (int56[] memory tickCumulatives, ) = IUniswapV3Pool(oracle).observe(
            secondsAgos
        );

        oracleTickCumulative = tickCumulatives[0];
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
            bool liquidated
        )
    {
        bytes32 key = keccak256(abi.encodePacked(recipient, id));
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
            uint128 _liquidityLocked
        ) = IMarginalV1Pool(pool).positions(key);

        // update for funding with library
        {
            PositionLibrary.Info memory info = PositionLibrary.Info({
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
                liquidityLocked: _liquidityLocked
            });

            (
                ,
                ,
                ,
                uint32 blockTimestampLast,
                int56 tickCumulativeLast,
                ,
                ,

            ) = getStateSynced(pool);

            int56 oracleTickCumulativeLast = getOracleSynced(pool);

            // sync if not settled or liquidated
            if (info.size > 0)
                info = info.sync(
                    blockTimestampLast,
                    tickCumulativeLast,
                    oracleTickCumulativeLast,
                    tickCumulativeRateMax,
                    fundingPeriod
                );

            zeroForOne = info.zeroForOne;
            size = info.size;
            debt = zeroForOne ? info.debt0 : info.debt1;
            margin = info.margin;
            liquidated = info.liquidated;
        }
    }
}
