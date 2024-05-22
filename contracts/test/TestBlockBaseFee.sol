// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

contract TestBlockBaseFee {
    uint256 public baseFee;

    event Set(uint256 baseFee);

    /// @dev Will be zero if no tx
    function query() external view returns (uint256) {
        return block.basefee;
    }

    /// @notice Should return block.basefee for tx
    function set() external returns (uint256) {
        baseFee = block.basefee;
        emit Set(block.basefee);
        return block.basefee;
    }
}
