// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3SwapCallback} from "@uniswap/v3-core/contracts/interfaces/callback/IUniswapV3SwapCallback.sol";

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";
import {TransferHelper} from "@marginal/v1-core/contracts/libraries/TransferHelper.sol";

contract MockUniswapV3Pool {
    address public immutable token0;
    address public immutable token1;
    uint24 public immutable fee;

    struct Observation {
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint160 secondsPerLiquidityCumulativeX128;
        bool initialized;
    }
    Observation[65535] public observations;
    uint256 private observationIndex;

    struct Slot0 {
        // the current price
        uint160 sqrtPriceX96;
        // the current tick
        int24 tick;
        // the most-recently updated index of the observations array
        uint16 observationIndex;
        // the current maximum number of observations that are being stored
        uint16 observationCardinality;
        // the next maximum number of observations to store, triggered in observations.write
        uint16 observationCardinalityNext;
        // the current protocol fee as a percentage of the swap fee taken on withdrawal
        // represented as an integer denominator (1/x)%
        uint32 feeProtocol;
        // whether the pool is locked
        bool unlocked;
    }
    Slot0 public slot0;

    // accumulated protocol fees in token0/token1 units
    struct ProtocolFees {
        uint128 token0;
        uint128 token1;
    }
    ProtocolFees public protocolFees;

    uint128 public liquidity;

    event Swap(
        address indexed sender,
        address indexed recipient,
        int256 amount0,
        int256 amount1,
        uint160 sqrtPriceX96,
        uint128 liquidity,
        int24 tick
    );

    constructor(address tokenA, address tokenB, uint24 _fee) {
        (address _token0, address _token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        token0 = _token0;
        token1 = _token1;
        fee = _fee;
    }

    function setSlot0(Slot0 memory _slot0) external {
        slot0 = _slot0;
    }

    function setLiquidity(uint128 _liquidity) external {
        liquidity = _liquidity;
    }

    function nextObservationIndex() external view returns (uint256) {
        return observationIndex % 65535;
    }

    function pushObservation(
        uint32 blockTimestamp,
        int56 tickCumulative,
        uint160 secondsPerLiquidityCumulativeX128,
        bool initialized
    ) external {
        observations[observationIndex % 65535] = (
            Observation({
                blockTimestamp: blockTimestamp,
                tickCumulative: tickCumulative,
                secondsPerLiquidityCumulativeX128: secondsPerLiquidityCumulativeX128,
                initialized: initialized
            })
        );
        observationIndex++;
    }

    /// @dev unlike Uniswap V3, naively returns back observations so order matters
    /// @dev assumes contracts query with e.g. secondsAgos[0] = secondsAgo; secondsAgos[1] = 0;
    // TODO: fix to be more realistic
    function observe(
        uint32[] calldata secondsAgos
    )
        external
        view
        returns (
            int56[] memory tickCumulatives,
            uint160[] memory secondsPerLiquidityCumulativeX128s
        )
    {
        uint256 _observationIndex = observationIndex;
        require(
            secondsAgos.length <= _observationIndex,
            "not enough observations"
        );
        tickCumulatives = new int56[](secondsAgos.length);
        secondsPerLiquidityCumulativeX128s = new uint160[](secondsAgos.length);
        for (uint256 i = 0; i < secondsAgos.length; i++) {
            uint256 j = _observationIndex - secondsAgos.length + i;
            Observation memory observation = observations[j];
            tickCumulatives[i] = observation.tickCumulative;
            secondsPerLiquidityCumulativeX128s[i] = observation
                .secondsPerLiquidityCumulativeX128;
        }
    }

    function increaseObservationCardinalityNext(
        uint16 observationCardinalityNext
    ) external {
        slot0.observationCardinalityNext = observationCardinalityNext;
    }

    /// @dev simple swap similar to marginal pool
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1) {
        Slot0 memory _slot0 = slot0;
        uint128 _liquidity = liquidity;

        require(amountSpecified != 0, "invalid amount specified");
        require(
            zeroForOne
                ? (sqrtPriceLimitX96 < _slot0.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : (sqrtPriceLimitX96 > _slot0.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO),
            "invalid sqrtPriceLimitX96"
        );
        bool exactInput = amountSpecified > 0;
        int256 amountSpecifiedLessFee = exactInput
            ? amountSpecified -
                int256(SwapMath.swapFees(uint256(amountSpecified), fee, false))
            : amountSpecified;

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            _liquidity,
            _slot0.sqrtPriceX96,
            zeroForOne,
            amountSpecifiedLessFee
        );
        require(
            zeroForOne
                ? sqrtPriceX96Next >= sqrtPriceLimitX96
                : sqrtPriceX96Next <= sqrtPriceLimitX96,
            "sqrtPriceX96 exceeds limit"
        );

        (amount0, amount1) = SwapMath.swapAmounts(
            _liquidity,
            _slot0.sqrtPriceX96,
            sqrtPriceX96Next
        );
        if (!zeroForOne) {
            amount0 = !exactInput ? amountSpecified : amount0;
            if (amount0 < 0)
                TransferHelper.safeTransfer(
                    token0,
                    recipient,
                    uint256(-amount0)
                );
            uint256 fees1 = exactInput
                ? uint256(amountSpecified) - uint256(amount1)
                : SwapMath.swapFees(uint256(amount1), fee, true);
            amount1 += int256(fees1);

            uint256 balance1Before = IERC20(token1).balanceOf(address(this));
            IUniswapV3SwapCallback(msg.sender).uniswapV3SwapCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance1Before + uint256(amount1) <=
                    IERC20(token1).balanceOf(address(this)),
                "amount1 less than min"
            );

            uint256 delta = _slot0.feeProtocol > 0
                ? fees1 / _slot0.feeProtocol
                : 0;
            if (delta > 0) protocolFees.token1 += uint128(delta);

            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _liquidity,
                    _slot0.sqrtPriceX96,
                    amount0,
                    amount1 - int256(delta)
                );
            liquidity = liquidityAfter;
            _slot0.sqrtPriceX96 = sqrtPriceX96After;
            _slot0.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        } else {
            amount1 = !exactInput ? amountSpecified : amount1;
            if (amount1 < 0)
                TransferHelper.safeTransfer(
                    token1,
                    recipient,
                    uint256(-amount1)
                );
            uint256 fees0 = exactInput
                ? uint256(amountSpecified) - uint256(amount0)
                : SwapMath.swapFees(uint256(amount0), fee, true);
            amount0 += int256(fees0);

            uint256 balance0Before = IERC20(token0).balanceOf(address(this));
            IUniswapV3SwapCallback(msg.sender).uniswapV3SwapCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance0Before + uint256(amount0) <=
                    IERC20(token0).balanceOf(address(this)),
                "amount0 less than min"
            );

            uint256 delta = _slot0.feeProtocol > 0
                ? fees0 / _slot0.feeProtocol
                : 0;
            if (delta > 0) protocolFees.token0 += uint128(delta);

            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _liquidity,
                    _slot0.sqrtPriceX96,
                    amount0 - int256(delta),
                    amount1
                );
            liquidity = liquidityAfter;
            _slot0.sqrtPriceX96 = sqrtPriceX96After;
            _slot0.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        }

        slot0 = _slot0;

        emit Swap(
            msg.sender,
            recipient,
            amount0,
            amount1,
            slot0.sqrtPriceX96,
            liquidity,
            slot0.tick
        );
    }
}
