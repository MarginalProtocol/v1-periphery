// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

/// @dev Fork of Uniswap V3 periphery PoolAddress.sol
library PoolAddress {
    bytes32 internal constant POOL_INIT_CODE_HASH =
        0x9137ab30ed13a078e93139dab3b7c06a2abbfbc0bb5bb9cd7e30b717f0ff4d25;

    /// @notice The identifying key of the pool
    struct PoolKey {
        address token0;
        address token1;
        uint24 maintenance;
    }

    /// @notice Returns PoolKey: the ordered tokens with the matched fee levels
    /// @param tokenA The first token of a pool, unsorted
    /// @param tokenB The second token of a pool, unsorted
    /// @param maintenance The maintenance level of the pool
    /// @return Poolkey The pool details with ordered token0 and token1 assignments
    function getPoolKey(
        address tokenA,
        address tokenB,
        uint24 maintenance
    ) internal pure returns (PoolKey memory) {
        if (tokenA > tokenB) (tokenA, tokenB) = (tokenB, tokenA);
        return
            PoolKey({token0: tokenA, token1: tokenB, maintenance: maintenance});
    }

    /// @notice Deterministically computes the pool address given the factory and PoolKey
    /// @param deployer The deployer contract address
    /// @param factory The factory contract address
    /// @param key The PoolKey
    /// @return pool The contract address of the pool
    function computeAddress(
        address deployer,
        address factory,
        PoolKey memory key
    ) internal pure returns (address pool) {
        require(key.token0 < key.token1);
        pool = address(
            uint160(
                uint256(
                    keccak256(
                        abi.encodePacked(
                            hex"ff",
                            deployer,
                            keccak256(
                                abi.encode(
                                    factory,
                                    key.token0,
                                    key.token1,
                                    key.maintenance
                                )
                            ),
                            POOL_INIT_CODE_HASH
                        )
                    )
                )
            )
        );
    }
}
