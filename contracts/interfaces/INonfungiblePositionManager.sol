// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import {IPeripheryImmutableState} from "./IPeripheryImmutableState.sol";
import {IPeripheryPayments} from "./IPeripheryPayments.sol";

/// @title The interface of the non-fungible token for Marginal v1 leverage positions
/// @notice Wraps Marginal v1 leverage positions in a non-fungible token to allow for transfers
interface INonfungiblePositionManager is IERC721 {
    /// @notice Returns details of an existing position
    /// @param tokenId The NFT token id associated with the position
    /// @dev Do *NOT* use in callback. Vulnerable to re-entrancy view issues.
    /// @return pool The pool address position taken out on
    /// @return positionId The position ID stored in the pool for the associated position
    /// @return zeroForOne Whether position settlement requires debt in of token0 for size + margin out of token1
    /// @return size The position size on the pool in the margin token
    /// @return debt The position debt owed to the pool in the non-margin token
    /// @return margin The margin backing the position on the pool
    /// @return safeMarginMinimum The minimum margin requirements necessary to keep position open on pool while also being safe from liquidation
    /// @return liquidated Whether the position has been liquidated
    /// @return safe Whether the position can be liquidated
    /// @return rewards The reward available to liquidators when position not safe
    function positions(
        uint256 tokenId
    )
        external
        view
        returns (
            address pool,
            uint96 positionId,
            bool zeroForOne,
            uint128 size,
            uint128 debt,
            uint128 margin,
            uint128 safeMarginMinimum,
            bool liquidated,
            bool safe,
            uint256 rewards
        );

    struct MintParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        bool zeroForOne;
        uint128 sizeDesired;
        uint128 sizeMinimum;
        uint128 debtMaximum;
        uint256 amountInMaximum;
        uint160 sqrtPriceLimitX96;
        uint128 margin;
        address recipient;
        uint256 deadline;
    }

    /// @notice Mints a new position, opening on pool
    /// @dev If a contract, `msg.sender` must implement a `receive()` function to receive any refunded excess liquidation rewards in the native (gas) token from the manager.
    /// @param params The parameters necessary for the position mint, encoded as `MintParams` in calldata
    /// @return tokenId The NFT token id associated with the minted position
    /// @return size The position size on the pool in the margin token
    /// @return debt The position debt owed to the pool in the non-margin token
    /// @return margin The amount of margin token in used to open the position
    /// @return fees The amount of fees in margin token paid to open the position
    /// @return rewards The amount of liquidation rewards in native (gas) token escrowed in opened position
    function mint(
        MintParams calldata params
    )
        external
        payable
        returns (
            uint256 tokenId,
            uint256 size,
            uint256 debt,
            uint256 margin,
            uint256 fees,
            uint256 rewards
        );

    struct LockParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        uint128 marginIn;
        uint256 deadline;
    }

    /// @dev Adds margin to an existing position
    /// @param params The parameters necessary for adding margin to the position, encoded as `LockParams` in calldata
    /// @return margin The margin backing the position after calling lock
    function lock(
        LockParams calldata params
    ) external payable returns (uint256 margin);

    struct FreeParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        uint128 marginOut;
        address recipient;
        uint256 deadline;
    }

    /// @notice Removes margin from an existing position
    /// @param params The parameters necessary for removing margin from the position, encoded as `FreeParams` in calldata
    /// @return margin The margin backing the position after calling free
    function free(FreeParams calldata params) external returns (uint256 margin);

    struct BurnParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        address recipient;
        uint256 deadline;
    }

    /// @notice Burns an existing position, settling on pool via external payer
    /// @dev If a contract, `msg.sender` must implement a `receive()` function to receive any refunded excess debt payment in the native (gas) token from the manager.
    /// @param params The parameters necessary for settling the position, encoded as `BurnParams` in calldata
    /// @return amountIn The amount of debt token in used to settle position
    /// @return amountOut The amount of margin token received after settling position
    /// @return rewards The amount of escrowed liquidation rewards in native (gas) token received after settling position
    function burn(
        BurnParams calldata params
    )
        external
        payable
        returns (uint256 amountIn, uint256 amountOut, uint256 rewards);

    struct IgniteParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        uint256 amountOutMinimum;
        address recipient;
        uint256 deadline;
    }

    /// @notice Burns an existing position, settling on pool via swap through spot
    /// @dev If a contract, `recipient` must implement a `receive()` function to receive any excess liquidation rewards unused by the spot swap in the native (gas) token from the manager.
    /// @param params The parameters necessary for settling the position, encoded as `IgniteParams` in calldata
    /// @return amountOut The amount of margin token received after settling position
    /// @return rewards The amount of escrowed liquidation rewards in native (gas) token received after settling position
    function ignite(
        IgniteParams calldata params
    ) external returns (uint256 amountOut, uint256 rewards);
}
