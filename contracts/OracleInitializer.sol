// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {PoolAddress} from "@uniswap/v3-periphery/contracts/libraries/PoolAddress.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PoolConstants} from "./libraries/PoolConstants.sol";

import {IOracleInitializer} from "./interfaces/IOracleInitializer.sol";

/// @title Initializer for Uniswap v3 oracles
/// @notice Provides methods for initializing Uniswap v3 oracles over multiple calls
contract OracleInitializer is IOracleInitializer, PeripheryImmutableState {
    /// @inheritdoc IOracleInitializer
    uint256 public immutable rebate;

    /// @inheritdoc IOracleInitializer
    mapping(address => uint256) public balances;

    event Escrow(address indexed pool, uint256 amount);
    event Increase(
        address indexed pool,
        address indexed recipient,
        uint16 observationCardinalityNext
    );

    error InvalidPool();
    error InvalidObservationCardinality(uint16 observationCardinality);

    constructor(
        address _factory,
        address _WETH9,
        uint256 _rebate
    ) PeripheryImmutableState(_factory, _WETH9) {
        rebate = _rebate;
    }

    /// @dev Returns the Uniswap v3 pool for the given token pair and fee tier. Reverts if pool contract does not exist.
    function getPoolAddress(
        address tokenA,
        address tokenB,
        uint24 fee
    ) private view returns (address pool) {
        pool = IUniswapV3Factory(uniswapV3Factory).getPool(tokenA, tokenB, fee);
        if (pool == address(0)) revert InvalidPool();
    }

    /// @inheritdoc IOracleInitializer
    function escrow(PoolAddress.PoolKey calldata poolKey) external payable {
        address pool = getPoolAddress(
            poolKey.token0,
            poolKey.token1,
            poolKey.fee
        );
        balances[pool] += msg.value;
        emit Escrow(pool, msg.value);
    }

    /// @inheritdoc IOracleInitializer
    function increase(
        PoolAddress.PoolKey calldata poolKey,
        address recipient,
        uint16 observationCardinalityNext
    ) external {
        address pool = getPoolAddress(
            poolKey.token0,
            poolKey.token1,
            poolKey.fee
        );

        balances[pool] -= rebate;
        IUniswapV3Pool(pool).increaseObservationCardinalityNext(
            observationCardinalityNext
        );
        // rebate at end of function to avoid re-entrancy with fallback
        TransferHelper.safeTransferETH(recipient, rebate);

        emit Increase(address(pool), recipient, observationCardinalityNext);
    }

    /// @inheritdoc IOracleInitializer
    function secondsRemaining(
        PoolAddress.PoolKey calldata poolKey
    ) external view returns (uint32) {
        address pool = getPoolAddress(
            poolKey.token0,
            poolKey.token1,
            poolKey.fee
        );
        uint16 observationCardinalityMinimum = IMarginalV1Factory(factory)
            .observationCardinalityMinimum();
        (
            ,
            ,
            uint16 observationIndex,
            uint16 observationCardinality,
            ,
            ,

        ) = IUniswapV3Pool(pool).slot0();
        if (observationCardinality < observationCardinalityMinimum)
            revert InvalidObservationCardinality(observationCardinality);

        (uint32 blockTimestampLast, , , ) = IUniswapV3Pool(pool).observations(
            observationIndex
        );

        // find oldest observation
        // TODO: fix if just grew oracle observations array (?)
        uint256 o = (observationIndex + 1) % observationCardinality;
        (uint32 blockTimestampFirst, , , ) = IUniswapV3Pool(pool).observations(
            o
        );

        uint32 delta;
        unchecked {
            delta = blockTimestampLast - blockTimestampFirst;
        }
        if (delta >= PoolConstants.secondsAgo) return 0;
        return (PoolConstants.secondsAgo - delta);
    }
}
