// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {PoolAddress} from "../libraries/PoolAddress.sol";
import {IPeripheryPayments} from "../interfaces/IPeripheryPayments.sol";
import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";

abstract contract PeripheryPayments is
    IPeripheryPayments,
    PeripheryImmutableState
{
    receive() external payable {
        // WETH9 if unwrap, pool when receiving escrowed liquidation rewards
        require(
            msg.sender == WETH9 || PoolAddress.isPool(factory, msg.sender),
            "Not WETH9 or pool"
        );
    }

    /// @inheritdoc IPeripheryPayments
    function unwrapWETH9(
        uint256 amountMinimum,
        address recipient
    ) public payable override {
        uint256 balanceWETH9 = IWETH9(WETH9).balanceOf(address(this));
        require(balanceWETH9 >= amountMinimum, "Insufficient WETH9");

        if (balanceWETH9 > 0) {
            IWETH9(WETH9).withdraw(balanceWETH9);
            TransferHelper.safeTransferETH(recipient, balanceWETH9);
        }
    }

    /// @inheritdoc IPeripheryPayments
    function sweepToken(
        address token,
        uint256 amountMinimum,
        address recipient
    ) public payable override {
        uint256 balanceToken = IERC20(token).balanceOf(address(this));
        require(balanceToken >= amountMinimum, "Insufficient token");

        if (balanceToken > 0) {
            TransferHelper.safeTransfer(token, recipient, balanceToken);
        }
    }

    /// @inheritdoc IPeripheryPayments
    function refundETH() external payable override {
        if (address(this).balance > 0)
            TransferHelper.safeTransferETH(msg.sender, address(this).balance);
    }

    /// @inheritdoc IPeripheryPayments
    function sweepETH(uint256 amountMinimum, address recipient) public payable {
        uint256 balanceETH = address(this).balance;
        require(balanceETH >= amountMinimum, "Insufficient ETH");

        if (balanceETH > 0)
            TransferHelper.safeTransferETH(recipient, balanceETH);
    }

    /// @notice Wraps balance of native (gas) token in contract to WETH9
    function wrapETH() internal {
        if (address(this).balance > 0)
            IWETH9(WETH9).deposit{value: address(this).balance}();
    }

    /// @notice Pay ERC20 token to recipient
    /// @param token The token to pay
    /// @param payer The entity that must pay
    /// @param recipient The entity that will receive payment
    /// @param value The amount to pay
    function pay(
        address token,
        address payer,
        address recipient,
        uint256 value
    ) internal {
        if (token == WETH9 && address(this).balance >= value) {
            // pay with WETH9
            IWETH9(WETH9).deposit{value: value}(); // wrap only what is needed to pay
            IWETH9(WETH9).transfer(recipient, value);
        } else if (payer == address(this)) {
            // pay with tokens already in the contract (for the exact input multihop case)
            TransferHelper.safeTransfer(token, recipient, value);
        } else {
            // pull payment
            TransferHelper.safeTransferFrom(token, payer, recipient, value);
        }
    }

    /// @notice Balance of ERC20 token held by this contract
    /// @param token The token to check
    /// @return value The balance amount
    function balance(address token) internal view returns (uint256 value) {
        return IERC20(token).balanceOf(address(this));
    }
}
