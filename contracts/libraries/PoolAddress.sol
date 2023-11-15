// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

/// @dev Fork of Uniswap V3 periphery PoolAddress.sol
library PoolAddress {
    error PoolInactive();

    /// @notice The identifying key of the pool
    struct PoolKey {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
    }

    /// @notice Returns PoolKey: the ordered tokens with the matched fee levels
    /// @param tokenA The first token of a pool, unsorted
    /// @param tokenB The second token of a pool, unsorted
    /// @param maintenance The maintenance level of the pool
    /// @param oracle The contract address of the oracle referenced by the pool
    /// @return PoolKey The pool details with ordered token0 and token1 assignments
    function getPoolKey(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) internal pure returns (PoolKey memory) {
        if (tokenA > tokenB) (tokenA, tokenB) = (tokenB, tokenA);
        return
            PoolKey({
                token0: tokenA,
                token1: tokenB,
                maintenance: maintenance,
                oracle: oracle
            });
    }

    /// @notice Gets the pool address from factory given pool key
    /// @dev Reverts if pool not created yet
    /// @param factory The factory contract address
    /// @param key The pool key
    /// @return pool The contract address of the pool
    function getAddress(
        address factory,
        PoolKey memory key
    ) internal view returns (address pool) {
        pool = IMarginalV1Factory(factory).getPool(
            key.token0,
            key.token1,
            key.maintenance,
            key.oracle
        );
        if (pool == address(0)) revert PoolInactive();
    }
}
