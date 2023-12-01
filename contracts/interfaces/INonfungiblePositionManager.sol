// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import {IPeripheryImmutableState} from "./IPeripheryImmutableState.sol";
import {IPeripheryPayments} from "./IPeripheryPayments.sol";

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
    /// @return marginMinimum The minimum margin requirements necessary to keep position open on pool
    /// @return liquidated Whether the position has been liquidated
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
            uint128 marginMinimum,
            bool liquidated,
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
    /// @param params The parameters necessary for the position mint, encoded as `MintParams` in calldata
    /// @return tokenId The NFT token id associated with the minted position
    /// @return size The position size on the pool in the margin token
    /// @return debt The position debt owed to the pool in the non-margin token
    /// @return amountIn The amount of margin token in used to open the position, including fees and liquidation rewards set aside in pool
    function mint(
        MintParams calldata params
    )
        external
        payable
        returns (uint256 tokenId, uint256 size, uint256 debt, uint256 amountIn);

    struct LockParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        uint128 marginIn;
        address recipient;
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
    function free(
        FreeParams calldata params
    ) external payable returns (uint256 margin);

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
    /// @param params The parameters necessary for settling the position, encoded as `BurnParams` in calldata
    /// @return amountIn The amount of debt token in used to settle position
    /// @return amountOut The amount of margin token received after settling position
    function burn(
        BurnParams calldata params
    ) external payable returns (uint256 amountIn, uint256 amountOut);

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
    /// @param params The parameters necessary for settling the position, encoded as `IgniteParams` in calldata
    /// @return amountOut The amount of margin token received after settling position
    function ignite(
        IgniteParams calldata params
    ) external payable returns (uint256 amountOut);

    struct GrabParams {
        address token0;
        address token1;
        uint24 maintenance;
        address oracle;
        uint256 tokenId;
        address recipient;
        uint256 deadline;
    }

    /// @notice Grabs an existing position, liquidating on pool
    /// @param params The parameters necessary for liquidating a position, encoded as `GrabParams` in calldata
    /// @return rewards The liquidation rewards received after liquidating the position
    function grab(
        GrabParams calldata params
    ) external payable returns (uint256 rewards);
}
