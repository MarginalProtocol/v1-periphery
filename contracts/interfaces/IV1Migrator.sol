// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

/// @title The interface of the v1 Migrator
/// @notice Migrates liquidity from Uniswap v3-compatible pairs into Marginal v1 pools
interface IV1Migrator {
    struct MigrateParams {
        uint256 tokenId; // tokenId of the Uniswap v3 NFT position to migrate
        uint128 liquidityDelta; // liquidity to migrate
        uint24 maintenance;
        uint256 amount0Min;
        uint256 amount1Min;
        address recipient;
        uint256 deadline;
        bool refundAsETH;
    }

    /// @notice Migrates liquidity to Marginal v1 by removing liquidity from Uniswap v3
    /// @dev Slippage protection is enforced via `amount{0,1}Min`, which should be a discount of the expected values of
    /// the maximum amount of Marginal v1 liquidity that the Uniswap v3 liquidity can get.
    /// @param params The params necessary to migrate liquidity, encoded as `MigrateParams` in calldata
    function migrate(MigrateParams calldata params) external;
}
