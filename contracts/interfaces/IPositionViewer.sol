// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

/// @title The interface of the position viewer for Marginal v1 pools
/// @notice Gets the synced positions on Marginal v1 pools
interface IPositionViewer {
    /// @notice Returns details of an existing position on pool
    /// @dev `secondsAgo` parameter useful in case extreme oracle observation activity and need to set < PoolConstants.secondsAgo
    /// @param pool The pool address position taken out on
    /// @param owner The owner address of the position
    /// @param id The position ID stored in the pool for the associated position
    /// @param secondsAgo The seconds ago to average the oracle TWAP over to calculate position safety attributes
    /// @return zeroForOne Whether position settlement requires debt in of token0 for size + margin out of token1
    /// @return size The position size on the pool in the margin token
    /// @return debt The position debt owed to the pool in the non-margin token
    /// @return margin The margin backing the position on the pool
    /// @return safeMarginMinimum The minimum margin requirements necessary to keep position open on pool while also being safe from liquidation
    /// @return liquidated Whether the position has been liquidated
    /// @return safe Whether the position can be liquidated
    /// @return rewards The reward available to liquidators when position not safe
    /// @return health The health factor of the position
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
        );
}
