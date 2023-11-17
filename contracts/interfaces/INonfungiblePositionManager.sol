// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.7.5;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import {IPeripheryImmutableState} from "./IPeripheryImmutableState.sol";
import {IPeripheryPayments} from "./IPeripheryPayments.sol";

interface INonfungiblePositionManager is IERC721 {
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
            bool liquidated
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
        uint160 sqrtPriceLimitX96;
        uint128 margin;
        address recipient;
        uint256 deadline;
    }

    /// @notice Mints a new position, opening on pool
    function mint(
        MintParams calldata params
    ) external payable returns (uint256 tokenId, uint256 size, uint256 debt);

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

    /// @notice Burns an existing position, settling on pool
    function burn(
        BurnParams calldata params
    ) external payable returns (uint256 amountIn, uint256 amountOut);

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
    function grab(
        GrabParams calldata params
    ) external payable returns (uint256 rewards);
}
