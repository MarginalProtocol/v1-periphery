// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

/// @title The interface of the v1 Migrator
/// @notice Migrates liquidity from Uniswap v3-compatible pairs into Marginal v1 pools
interface IV1Migrator {
    struct MigrateParams {
        uint256 tokenId; // tokenId of the Uniswap v3 NFT position to migrate
        uint128 liquidityToRemove; // liquidity to remove from Uniswap v3 NFT position
        uint256 amount0MinToRemove;
        uint256 amount1MinToRemove;
        uint8 percentageToMigrate; // represented as a numerator over 100
        uint256 amount0MinToMigrate;
        uint256 amount1MinToMigrate;
        uint24 maintenance;
        address recipient;
        uint256 deadline;
        bool refundAsETH;
    }

    /// @notice Migrates liquidity to Marginal v1 by removing liquidity from Uniswap v3
    /// @dev Slippage protection is enforced via `amount{0,1}MinToRemove` on Uniswap v3 decrease liquidity
    /// and `amount{0,1}MinToMigrate` on Marginal v1 add liquidity.
    /// Must approve `IV1Migrator` as spender of `params.tokenId` or set approval for all prior to calling migrate.
    /// @param params The params necessary to migrate liquidity, encoded as `MigrateParams` in calldata
    function migrate(MigrateParams calldata params) external;
}
