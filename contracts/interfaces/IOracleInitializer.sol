// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {PoolAddress} from "@uniswap/v3-periphery/contracts/libraries/PoolAddress.sol";

/// @title Interface for the Marginal v1 oracle initializer
/// @notice Provides methods for initializing Uniswap v3 oracles over multiple calls
interface IOracleInitializer {
    /// @notice Returns the rebate refunded in native gas token when calling `IOracleInitializer.sol::increase`
    /// @return The gas rebate
    function rebate() external view returns (uint256);

    /// @notice Returns the amount of native gas token escrowed for Uniswap v3 pool oracle initialization
    /// @return The amount of native gas token escrowed
    function balances(address pool) external view returns (uint256);

    /// @notice Escrows an amount of native gas token for Uniswap v3 pool oracle initialization
    /// @param poolKey The Uniswap v3 pool key
    function escrow(PoolAddress.PoolKey calldata poolKey) external payable;

    /// @notice Increases the next observation cardinality on a Uniswap v3 pool oracle
    /// @param poolKey The Uniswap v3 pool key
    /// @param recipient The recipient of the gas rebate for increasing the cardinality
    /// @param observationCardinalityNext The next observation cardinality to set the Uniswap v3 pool to
    function increase(
        PoolAddress.PoolKey calldata poolKey,
        address recipient,
        uint16 observationCardinalityNext
    ) external;

    /// @notice Returns the seconds remaining until a Uniswap v3 pool oracle has fully initialized
    /// @param poolKey The Uniswap v3 pool key
    /// @return The seconds remaining until oracle fully initialized
    function secondsRemaining(
        PoolAddress.PoolKey calldata poolKey
    ) external view returns (uint32);
}
