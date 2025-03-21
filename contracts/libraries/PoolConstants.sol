// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

/// @title PoolConstants
/// @notice A library for pool internal constants relevant for periphery contracts
library PoolConstants {
    uint24 internal constant fee = 1000; // 10 bps across all pools
    uint24 internal constant rewardPremium = 2000000; // 2x base fee as liquidation rewards
    uint24 internal constant tickCumulativeRateMax = 920; // bound on funding rate of ~10% per funding period

    uint32 internal constant secondsAgo = 43200; // 12 hr TWAP for oracle price
    uint32 internal constant fundingPeriod = 604800; // 7 day funding period

    // @dev varies for different chains
    uint256 internal constant blockBaseFeeMin = 4e8; // min base fee for liquidation rewards
    uint256 internal constant gasLiquidate = 150000; // gas required to call liquidate

    uint128 internal constant MINIMUM_LIQUIDITY = 10000; // liquidity locked on initial mint always available for swaps
    uint128 internal constant MINIMUM_SIZE = 10000; // minimum position size, debt, insurance amounts to prevent dust sizes
}
