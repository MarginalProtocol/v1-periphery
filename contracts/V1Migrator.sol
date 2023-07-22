// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity =0.8.15;

import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";
import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {INonfungiblePositionManager as IUniswapV3NonfungiblePositionManager} from "@uniswap/v3-periphery/contracts/interfaces/INonfungiblePositionManager.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {SelfPermit} from "@uniswap/v3-periphery/contracts/base/SelfPermit.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PoolInitializer} from "./base/PoolInitializer.sol";
import {ISwapRouter} from "./interfaces/ISwapRouter.sol";
import {IV1Migrator} from "./interfaces/IV1Migrator.sol";

/// @title Marginal V1 Migrator
contract V1Migrator is
    IV1Migrator,
    PeripheryImmutableState,
    PoolInitializer,
    Multicall,
    SelfPermit
{
    address public immutable marginalV1SwapRouter;
    address public immutable uniswapV3NonfungiblePositionManager;

    modifier onlyApprovedOrOwner(uint256 tokenId) {
        if (!_isApprovedOrOwner(msg.sender, tokenId)) revert Unauthorized();
        _;
    }

    error Unauthorized();

    constructor(
        address _factory,
        address _WETH9,
        address _marginalV1SwapRouter,
        address _uniswapV3NonfungiblePositionManager
    ) PeripheryImmutableState(_factory, _WETH9) {
        marginalV1SwapRouter = _marginalV1SwapRouter;
        uniswapV3NonfungiblePositionManager = _uniswapV3NonfungiblePositionManager;
    }

    receive() external payable {
        require(msg.sender == WETH9, "Not WETH9");
    }

    function _isApprovedOrOwner(
        address spender,
        uint256 tokenId
    ) internal view returns (bool) {
        IUniswapV3NonfungiblePositionManager manager = IUniswapV3NonfungiblePositionManager(
                uniswapV3NonfungiblePositionManager
            );
        address owner = manager.ownerOf(tokenId);
        return (spender == owner ||
            manager.isApprovedForAll(owner, spender) ||
            manager.getApproved(tokenId) == spender);
    }

    function migrate(
        MigrateParams calldata params
    ) external onlyApprovedOrOwner(params.tokenId) {
        IUniswapV3NonfungiblePositionManager manager = IUniswapV3NonfungiblePositionManager(
                uniswapV3NonfungiblePositionManager
            ); // uniswap v3
        ISwapRouter router = ISwapRouter(marginalV1SwapRouter); // marginal v1

        manager.decreaseLiquidity(
            IUniswapV3NonfungiblePositionManager.DecreaseLiquidityParams({
                tokenId: params.tokenId,
                liquidity: params.liquidityToMigrate,
                amount0Min: params.amount0Min,
                amount1Min: params.amount1Min,
                deadline: params.deadline
            })
        );
        (uint256 amount0, uint256 amount1) = manager.collect(
            IUniswapV3NonfungiblePositionManager.CollectParams({
                tokenId: params.tokenId,
                recipient: address(this),
                amount0Max: type(uint128).max,
                amount1Max: type(uint128).max
            })
        );

        // approve marginal swap router to pull
        TransferHelper.safeApprove(params.token0, address(router), amount0);
        TransferHelper.safeApprove(params.token1, address(router), amount1);

        (, uint256 amount0Migrated, uint256 amount1Migrated) = router
            .addLiquidity(
                ISwapRouter.AddLiquidityParams({
                    token0: params.token0,
                    token1: params.token1,
                    maintenance: params.maintenance,
                    oracle: params.oracle,
                    recipient: params.recipient,
                    amount0Desired: amount0,
                    amount1Desired: amount1,
                    amount0Min: params.amount0Min, // TODO: should be diff from univ3 decreaseLiquidity?
                    amount1Min: params.amount1Min, // TODO: should be diff from univ3 decreaseLiquidity?
                    deadline: params.deadline
                })
            );

        // clear allowance and refund dust
        // ref @uniswap/v3-periphery/contracts/V3Migrator.sol#L71
        if (amount0Migrated < amount0) {
            TransferHelper.safeApprove(params.token0, address(router), 0);

            uint256 refund0 = amount0 - amount0Migrated;
            if (params.refundAsETH && params.token0 == WETH9) {
                IWETH9(WETH9).withdraw(refund0);
                TransferHelper.safeTransferETH(msg.sender, refund0);
            } else {
                TransferHelper.safeTransfer(params.token0, msg.sender, refund0);
            }
        }

        if (amount1Migrated < amount1) {
            TransferHelper.safeApprove(params.token1, address(router), 0);

            uint256 refund1 = amount1 - amount1Migrated;
            if (params.refundAsETH && params.token1 == WETH9) {
                IWETH9(WETH9).withdraw(refund1);
                TransferHelper.safeTransferETH(msg.sender, refund1);
            } else {
                TransferHelper.safeTransfer(params.token1, msg.sender, refund1);
            }
        }
    }
}
