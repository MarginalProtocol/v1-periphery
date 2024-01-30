// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";
import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {INonfungiblePositionManager as IUniswapV3NonfungiblePositionManager} from "@uniswap/v3-periphery/contracts/interfaces/INonfungiblePositionManager.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {IRouter} from "./interfaces/IRouter.sol";
import {IV1Migrator} from "./interfaces/IV1Migrator.sol";

/// @title Marginal v1 Migrator
/// @notice Migrates liquidity from Uniswap v3-compatible pairs into Marginal v1 pools
contract V1Migrator is IV1Migrator, PeripheryImmutableState, Multicall {
    address public immutable marginalV1Router;
    address public immutable uniswapV3NonfungiblePositionManager;

    modifier onlyApprovedOrOwner(uint256 tokenId) {
        if (!_isApprovedOrOwner(msg.sender, tokenId)) revert Unauthorized();
        _;
    }

    error Unauthorized();
    error LiquidityDeltaGreaterThanMax();

    constructor(
        address _factory,
        address _WETH9,
        address _marginalV1Router,
        address _uniswapV3NonfungiblePositionManager
    ) PeripheryImmutableState(_factory, _WETH9) {
        marginalV1Router = _marginalV1Router;
        uniswapV3NonfungiblePositionManager = _uniswapV3NonfungiblePositionManager;
    }

    receive() external payable {
        require(msg.sender == WETH9, "Not WETH9");
    }

    function _isApprovedOrOwner(
        address spender,
        uint256 tokenId
    ) internal view returns (bool) {
        IUniswapV3NonfungiblePositionManager uniswapV3Manager = IUniswapV3NonfungiblePositionManager(
                uniswapV3NonfungiblePositionManager
            );
        address owner = uniswapV3Manager.ownerOf(tokenId);
        return (spender == owner ||
            uniswapV3Manager.isApprovedForAll(owner, spender) ||
            uniswapV3Manager.getApproved(tokenId) == spender);
    }

    /// @inheritdoc IV1Migrator
    function migrate(
        MigrateParams calldata params
    ) external onlyApprovedOrOwner(params.tokenId) {
        IUniswapV3NonfungiblePositionManager uniswapV3Manager = IUniswapV3NonfungiblePositionManager(
                uniswapV3NonfungiblePositionManager
            ); // uniswap v3
        IRouter router = IRouter(marginalV1Router); // marginal v1

        (
            ,
            ,
            address token0,
            address token1,
            uint24 fee,
            ,
            ,
            uint128 liquidity,
            ,
            ,
            ,

        ) = uniswapV3Manager.positions(params.tokenId);
        address oracle = IUniswapV3Factory(uniswapV3Factory).getPool(
            token0,
            token1,
            fee
        );

        if (params.liquidityDelta > liquidity)
            revert LiquidityDeltaGreaterThanMax();
        uniswapV3Manager.decreaseLiquidity(
            IUniswapV3NonfungiblePositionManager.DecreaseLiquidityParams({
                tokenId: params.tokenId,
                liquidity: params.liquidityDelta,
                amount0Min: params.amount0Min,
                amount1Min: params.amount1Min,
                deadline: params.deadline
            })
        );
        (uint256 amount0, uint256 amount1) = uniswapV3Manager.collect(
            IUniswapV3NonfungiblePositionManager.CollectParams({
                tokenId: params.tokenId,
                recipient: address(this),
                amount0Max: type(uint128).max,
                amount1Max: type(uint128).max
            })
        );

        // approve marginal swap router to pull
        TransferHelper.safeApprove(token0, address(router), amount0);
        TransferHelper.safeApprove(token1, address(router), amount1);

        (, uint256 amount0Migrated, uint256 amount1Migrated) = router
            .addLiquidity(
                IRouter.AddLiquidityParams({
                    token0: token0,
                    token1: token1,
                    maintenance: params.maintenance,
                    oracle: oracle,
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
            TransferHelper.safeApprove(token0, address(router), 0);

            uint256 refund0 = amount0 - amount0Migrated;
            if (params.refundAsETH && token0 == WETH9) {
                IWETH9(WETH9).withdraw(refund0);
                TransferHelper.safeTransferETH(msg.sender, refund0);
            } else {
                TransferHelper.safeTransfer(token0, msg.sender, refund0);
            }
        }

        if (amount1Migrated < amount1) {
            TransferHelper.safeApprove(token1, address(router), 0);

            uint256 refund1 = amount1 - amount1Migrated;
            if (params.refundAsETH && token1 == WETH9) {
                IWETH9(WETH9).withdraw(refund1);
                TransferHelper.safeTransferETH(msg.sender, refund1);
            } else {
                TransferHelper.safeTransfer(token1, msg.sender, refund1);
            }
        }
    }
}
