// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";
import {FixedPoint192} from "@marginal/v1-core/contracts/libraries/FixedPoint192.sol";
import {OracleLibrary} from "@marginal/v1-core/contracts/libraries/OracleLibrary.sol";
import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";
import {PositionState} from "../base/PositionState.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

import {INonfungiblePositionManager} from "../interfaces/INonfungiblePositionManager.sol";
import {IOracle} from "../interfaces/IOracle.sol";

/// @title Oracle for Marginal v1 pools
/// @notice Quotes oracle related quantities for Marginal v1 pools
contract Oracle is IOracle, PeripheryImmutableState, PositionState, Multicall {
    INonfungiblePositionManager public immutable manager;

    constructor(
        address _factory,
        address _WETH9,
        address _manager
    ) PeripheryImmutableState(_factory, _WETH9) {
        manager = INonfungiblePositionManager(_manager);
    }

    /// @dev Returns the pool for the given token pair and maintenance. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1Pool) {
        return IMarginalV1Pool(PoolAddress.getAddress(factory, poolKey));
    }

    /// @inheritdoc IOracle
    function sqrtPricesX96(
        PoolAddress.PoolKey memory poolKey
    )
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint160 oracleSqrtPriceX96,
            uint256 fundingSqrtRatioX96
        )
    {
        IMarginalV1Pool pool = getPool(poolKey);

        bool initialized;
        (sqrtPriceX96, , , , , , , initialized) = pool.state();
        if (!initialized) revert("Not initialized");

        int56[] memory oracleTickCumulativesLast = getOracleSynced(
            address(pool)
        );
        oracleSqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
            OracleLibrary.oracleTickCumulativeDelta(
                oracleTickCumulativesLast[0],
                oracleTickCumulativesLast[1] // zero seconds ago
            ),
            PoolConstants.secondsAgo
        );

        // funding ratio for longs (zeroForOne = false) is anticipated funding rate over next funding period at current prices
        // @dev P / bar{P} for zeroForOne = false
        (uint160 uniswapV3SqrtPriceX96, , , , , , ) = IUniswapV3Pool(
            poolKey.oracle
        ).slot0();

        fundingSqrtRatioX96 =
            (uint256(sqrtPriceX96) << FixedPoint96.RESOLUTION) /
            uint256(uniswapV3SqrtPriceX96);
    }

    /// @inheritdoc IOracle
    function liquidationSqrtPriceX96(
        uint256 tokenId
    ) external view returns (uint160) {
        (
            address pool,
            ,
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            ,
            ,
            ,

        ) = manager.positions(tokenId);
        uint24 maintenance = IMarginalV1Pool(pool).maintenance();
        return
            liquidationSqrtPriceX96(
                zeroForOne,
                size,
                debt,
                margin,
                maintenance
            );
    }

    /// @inheritdoc IOracle
    function liquidationSqrtPriceX96(
        bool zeroForOne,
        uint128 size,
        uint128 debt,
        uint128 margin,
        uint24 maintenance
    ) public pure returns (uint160) {
        uint256 debtAdjusted = (uint256(debt) * (1e6 + uint256(maintenance))) /
            1e6;
        uint256 collateral = uint256(size) + uint256(margin);

        // sqrt(y/x) << 96
        uint256 num = !zeroForOne ? debtAdjusted : collateral;
        uint256 denom = !zeroForOne ? collateral : debtAdjusted;

        uint256 sqrtPriceX96 = (
            num <= type(uint64).max
                ? Math.sqrt((num << FixedPoint192.RESOLUTION) / denom)
                : (Math.sqrt(num) << FixedPoint96.RESOLUTION) / Math.sqrt(denom)
        );
        if (
            !(sqrtPriceX96 >= SqrtPriceMath.MIN_SQRT_RATIO &&
                sqrtPriceX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceX96");
        return uint160(sqrtPriceX96);
    }
}
