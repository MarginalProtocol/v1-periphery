// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;
pragma abicoder v2;

/// @title V1 Migrator
/// @notice Enables migration of liqudity from Uniswap v3-compatible pairs into Marginal v1 pools
interface IV1Migrator {
    struct MigrateParams {
        uint256 tokenId; // tokenId of the Uniswap v3 NFT position to migrate
        uint128 liquidityToMigrate;
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
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
