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
        uint96 id
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
        ) = getPositionSynced(pool, owner, id);

        uint24 maintenance = IMarginalV1Pool(pool).maintenance();
        int56[] memory oracleTickCumulativesLast = getOracleSynced(pool);
        uint160 oracleSqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
            OracleLibrary.oracleTickCumulativeDelta(
                oracleTickCumulativesLast[0],
                oracleTickCumulativesLast[1] // zero seconds ago
            ),
            PoolConstants.secondsAgo
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

    /// @inheritdoc IPositionViewer
    function getPositionInfoSynced(
        address pool,
        address recipient,
        uint96 id
    )
        public
        view
        returns (
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            bool liquidated,
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

        // sync if not settled or liquidated
        if (info.size > 0) {
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

                address oracle = IMarginalV1Pool(pool).oracle();

                // zero seconds ago for oracle tickCumulative
                uint32[] memory secondsAgos = new uint32[](1);
                (int56[] memory oracleTickCumulativesLast, ) = IUniswapV3Pool(
                    oracle
                ).observe(secondsAgos);

                info.sync(
                    blockTimestampLast,
                    tickCumulativeLast,
                    oracleTickCumulativesLast[0], // zero seconds ago
                    PoolConstants.tickCumulativeRateMax,
                    PoolConstants.fundingPeriod
                );
            }
        }

        debt = zeroForOne ? info.debt0 : info.debt1;
    }
}
