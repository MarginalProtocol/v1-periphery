// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";

contract MockUniswapV3PoolQuoter {
    constructor() {}

    /// @dev simple swap quote similar to marginal pool
    function quote(
        address pool,
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external view returns (int256 amount0, int256 amount1) {
        (uint160 _sqrtPriceX96, , , , , , ) = IUniswapV3Pool(pool).slot0();
        uint128 _liquidity = IUniswapV3Pool(pool).liquidity();
        uint24 fee = IUniswapV3Pool(pool).fee();

        require(amountSpecified != 0, "invalid amount specified");
        require(
            zeroForOne
                ? (sqrtPriceLimitX96 < _sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : (sqrtPriceLimitX96 > _sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO),
            "invalid sqrtPriceLimitX96"
        );
        bool exactInput = amountSpecified > 0;
        int256 amountSpecifiedLessFee = exactInput
            ? amountSpecified -
                int256(SwapMath.swapFees(uint256(amountSpecified), fee, false))
            : amountSpecified;

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            _liquidity,
            _sqrtPriceX96,
            zeroForOne,
            amountSpecifiedLessFee
        );
        require(
            zeroForOne
                ? sqrtPriceX96Next >= sqrtPriceLimitX96
                : sqrtPriceX96Next <= sqrtPriceLimitX96,
            "sqrtPriceX96 exceeds limit"
        );

        (amount0, amount1) = SwapMath.swapAmounts(
            _liquidity,
            _sqrtPriceX96,
            sqrtPriceX96Next
        );
        if (!zeroForOne) {
            amount0 = !exactInput ? amountSpecified : amount0;
            uint256 fees1 = exactInput
                ? uint256(amountSpecified) - uint256(amount1)
                : SwapMath.swapFees(uint256(amount1), fee, true);
            amount1 += int256(fees1);
        } else {
            amount1 = !exactInput ? amountSpecified : amount1;
            uint256 fees0 = exactInput
                ? uint256(amountSpecified) - uint256(amount0)
                : SwapMath.swapFees(uint256(amount0), fee, true);
            amount0 += int256(fees0);
        }
    }
}
