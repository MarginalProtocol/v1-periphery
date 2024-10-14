// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {PositionState} from "../base/PositionState.sol";
import {IPositionViewer} from "../interfaces/IPositionViewer.sol";

/// @title Position viewer for Marginal v1 pools
/// @notice View of synced positions on Marginal v1 pools that may not have be minted via the NFT position manager
contract PositionViewer is IPositionViewer, PositionState {
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
        ) = _getPositionSynced(pool, owner, id, secondsAgo);
    }
}
