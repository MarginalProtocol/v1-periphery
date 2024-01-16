// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity =0.8.15;

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {IPoolInitializer} from "../interfaces/IPoolInitializer.sol";

/// @title Creates and initializes V1 Pools
/// @dev Fork of Uniswap V3 periphery PoolInitializer.sol, adapted to Marginal V1
abstract contract PoolInitializer is IPoolInitializer, PeripheryImmutableState {
    error InvalidOracle();

    /// @inheritdoc IPoolInitializer
    function initializeOracleIfNecessary(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 uniswapV3Fee,
        uint16 observationCardinalityNext
    ) external override {
        require(token0 < token1);
        address oracle = IUniswapV3Factory(uniswapV3Factory).getPool(
            token0,
            token1,
            uniswapV3Fee
        );
        if (oracle == address(0)) revert InvalidOracle();

        (
            ,
            ,
            ,
            ,
            uint16 observationCardinalityNextExisting,
            ,

        ) = IUniswapV3Pool(oracle).slot0();
        uint16 observationCardinalityMinimum = IMarginalV1Factory(factory)
            .observationCardinalityMinimum();
        require(
            observationCardinalityNextExisting < observationCardinalityNext &&
                observationCardinalityMinimum <= observationCardinalityNext
        );

        if (
            observationCardinalityNextExisting < observationCardinalityMinimum
        ) {
            IUniswapV3Pool(oracle).increaseObservationCardinalityNext(
                observationCardinalityNext
            );
        }
    }
}
