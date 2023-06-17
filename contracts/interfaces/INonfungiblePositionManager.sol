// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.7.5;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import {IPeripheryImmutableState} from "./IPeripheryImmutableState.sol";
import {IPeripheryPayments} from "./IPeripheryPayments.sol";

// TODO:
interface INonfungiblePositionManager is
    IPeripheryPayments,
    IPeripheryImmutableState,
    IERC721
{

}
