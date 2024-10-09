// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {OracleLibrary} from "@marginal/v1-core/contracts/libraries/OracleLibrary.sol";
import {Position as PositionLibrary} from "@marginal/v1-core/contracts/libraries/Position.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PositionState} from "../base/PositionState.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

import {IOracle} from "../interfaces/IOracle.sol";
import {IPositionViewer} from "../interfaces/IPositionViewer.sol";

/// @title Position viewer for Marginal v1 pools
/// @notice View of synced positions on Marginal v1 pools that may not have be minted via the NFT position manager
contract PositionViewer is IPositionViewer, PositionState {
    using PositionLibrary for PositionLibrary.Info;

    /// @inheritdoc IPositionViewer
    address public immutable oracle;

    constructor(address _oracle) {
        oracle = _oracle;
    }

    /// @inheritdoc IPositionViewer
    function positions(
        address pool,
        address owner,
        uint96 id,
        uint32 secondsAgo
    )
        external
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
            uint256 healthFactor
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
            rewards
        ) = getPositionSynced(pool, owner, id, secondsAgo);

        uint24 maintenance = IMarginalV1Pool(pool).maintenance();
        int56[] memory oracleTickCumulativesLast = getOracleSynced(
            pool,
            secondsAgo
        );
        uint160 oracleSqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
            OracleLibrary.oracleTickCumulativeDelta(
                oracleTickCumulativesLast[0],
                oracleTickCumulativesLast[1] // zero seconds ago
            ),
            secondsAgo
        );

        healthFactor = IOracle(oracle).healthFactor(
            zeroForOne,
            size,
            debt,
            margin,
            maintenance,
            oracleSqrtPriceX96
        );
    }

    /// @notice Gets external oracle tick cumulative values for time deltas: [secondsAgo, 0]
    /// @param pool The pool to get external oracle state for
    function getOracleSynced(
        address pool,
        uint32 secondsAgo
    ) internal view returns (int56[] memory oracleTickCumulatives) {
        address oracle = IMarginalV1Pool(pool).oracle();

        // zero seconds ago for oracle tickCumulative
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;

        (oracleTickCumulatives, ) = IUniswapV3Pool(oracle).observe(secondsAgos);
    }

    /// @notice Gets pool position synced for funding updates
    /// @param pool The pool the position is on
    /// @param recipient The recipient of the position at open
    /// @param id The position id
    function getPositionSynced(
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
            uint256 rewards
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

                int56[] memory oracleTickCumulativesLast = getOracleSynced(
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

            safe = info.safe(
                OracleLibrary.oracleSqrtPriceX96(
                    oracleTickCumulativeDelta,
                    secondsAgo
                ),
                maintenance
            );
            safeMarginMinimum = _safeMarginMinimum(
                info,
                marginMinimum,
                maintenance,
                oracleTickCumulativeDelta,
                secondsAgo
            );
        }

        debt = zeroForOne ? info.debt0 : info.debt1;
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
}
