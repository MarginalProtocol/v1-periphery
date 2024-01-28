// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

/// @notice Interface for the Eden network Uniswap v3 static quoter with public quote method
/// @dev Ref @eden-network/uniswap-v3-static-quoter/contracts/UniV3likeQuoterCore.sol
interface IUniswapV3StaticQuoter {
    /// @notice Quotes the swap on the Uniswap v3 pool
    /// @param poolAddress The address of the Uniswap v3 pool
    /// @param zeroForOne Whether the swap is token0 in and token1 out
    /// @param amountSpecified The amount to send or receive from pool
    /// @param sqrtPriceLimitX96 The sqrt price at which to stop swapping
    /// @return amount0 The amount of token0 in/out to pool
    /// @return amount1 The amount of token1 in/out to pool
    function quote(
        address poolAddress,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external view returns (int256 amount0, int256 amount1);
}
