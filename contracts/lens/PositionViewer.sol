// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {OracleLibrary} from "@marginal/v1-core/contracts/libraries/OracleLibrary.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PositionState} from "../base/PositionState.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

import {IOracle} from "../interfaces/IOracle.sol";
import {IPositionViewer} from "../interfaces/IPositionViewer.sol";

/// @title Position viewer for Marginal v1 pools
/// @notice View of synced positions on Marginal v1 pools that may not have be minted via the NFT position manager
contract PositionViewer is IPositionViewer, PositionState {
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
}
