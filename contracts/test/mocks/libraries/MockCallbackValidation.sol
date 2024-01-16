// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {CallbackValidation} from "../../../libraries/CallbackValidation.sol";
import {PoolAddress} from "../../../libraries/PoolAddress.sol";

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

contract MockCallbackValidation {
    function verifyCallback(
        address factory,
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) external view returns (IMarginalV1Pool pool) {
        return
            CallbackValidation.verifyCallback(
                factory,
                tokenA,
                tokenB,
                maintenance,
                oracle
            );
    }

    function verifyCallback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) external view returns (IMarginalV1Pool pool) {
        return CallbackValidation.verifyCallback(factory, poolKey);
    }

    function verifyUniswapV3Callback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) external view returns (IUniswapV3Pool uniswapV3Pool) {
        return CallbackValidation.verifyUniswapV3Callback(factory, poolKey);
    }
}
