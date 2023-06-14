// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {IPeripheryPaymentsWithFee} from "@uniswap/v3-periphery/contracts/interfaces/IPeripheryPaymentsWithFee.sol";

import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {PeripheryPayments} from "./PeripheryPayments.sol";

abstract contract PeripheryPaymentsWithFee is
    PeripheryPayments,
    IPeripheryPaymentsWithFee
{
    /// @inheritdoc IPeripheryPaymentsWithFee
    function unwrapWETH9WithFee(
        uint256 amountMinimum,
        address recipient,
        uint256 feeBips,
        address feeRecipient
    ) public payable override {
        require(feeBips > 0 && feeBips <= 100);

        uint256 balanceWETH9 = IWETH9(WETH9).balanceOf(address(this));
        require(balanceWETH9 >= amountMinimum, "Insufficient WETH9");

        if (balanceWETH9 > 0) {
            IWETH9(WETH9).withdraw(balanceWETH9);
            uint256 feeAmount = (balanceWETH9 * feeBips) / 10_000;
            if (feeAmount > 0)
                TransferHelper.safeTransferETH(feeRecipient, feeAmount);
            TransferHelper.safeTransferETH(recipient, balanceWETH9 - feeAmount);
        }
    }

    /// @inheritdoc IPeripheryPaymentsWithFee
    function sweepTokenWithFee(
        address token,
        uint256 amountMinimum,
        address recipient,
        uint256 feeBips,
        address feeRecipient
    ) public payable override {
        require(feeBips > 0 && feeBips <= 100);

        uint256 balanceToken = IERC20(token).balanceOf(address(this));
        require(balanceToken >= amountMinimum, "Insufficient token");

        if (balanceToken > 0) {
            uint256 feeAmount = (balanceToken * feeBips) / 10_000;
            if (feeAmount > 0)
                TransferHelper.safeTransfer(token, feeRecipient, feeAmount);
            TransferHelper.safeTransfer(
                token,
                recipient,
                balanceToken - feeAmount
            );
        }
    }
}
