// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity =0.8.19;

import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {IERC721Metadata} from "@openzeppelin/contracts/token/ERC721/extensions/IERC721Metadata.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

import {IMarginalV1Pool} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Pool.sol";

import {NFTSVG} from "./libraries/NFTSVG.sol";
import {SVGElements} from "./libraries/SVGElements.sol";

import {INonfungiblePositionManager} from "./interfaces/INonfungiblePositionManager.sol";
import {INonfungibleTokenPositionDescriptor} from "./interfaces/INonfungibleTokenPositionDescriptor.sol";

/// @title Non-fungible token position descriptor for Marginal v1 leverage positions
/// @author Sablier Labs
/// @notice Produces a string containing the data URI for a JSON metadata string
/// @dev Fork of Sablier V2 SablierV2NFTDescriptor for Marginal V1 leverage positions. Incorporates a bit of Uniswap V3 NonfungibleTokenPositionDescriptor code.
contract NonfungibleTokenPositionDescriptor is
    INonfungibleTokenPositionDescriptor
{
    using Strings for address;
    using Strings for string;
    using Strings for uint256;

    /*//////////////////////////////////////////////////////////////////////////
                           USER-FACING CONSTANT FUNCTIONS
    //////////////////////////////////////////////////////////////////////////*/

    /// @dev Needed to avoid Stack Too Deep.
    struct TokenURIVars {
        string quoteTokenSymbol;
        string baseTokenSymbol;
        string maxLeverageTier;
        address tokenSize;
        address tokenDebt;
        string symbolSize;
        string symbolDebt;
        uint8 decimalsSize;
        uint8 decimalsDebt;
        bool zeroForOne;
        uint256 amountSize;
        uint256 amountDebt;
        uint256 amountMargin;
        uint256 amountSafeMarginMinimum;
        string healthFactor;
        address poolAddress;
        string svg;
        string json;
    }

    /// @inheritdoc INonfungibleTokenPositionDescriptor
    function tokenURI(
        INonfungiblePositionManager positionManager,
        uint256 tokenId
    ) external view override returns (string memory) {
        TokenURIVars memory vars;

        (
            vars.poolAddress,
            ,
            vars.zeroForOne,
            vars.amountSize,
            vars.amountDebt,
            vars.amountMargin,
            vars.amountSafeMarginMinimum,
            ,
            ,

        ) = positionManager.positions(tokenId);
        vars.healthFactor = calculateHealthFactor(
            vars.amountMargin,
            vars.amountSafeMarginMinimum
        );

        uint24 maintenance = IMarginalV1Pool(vars.poolAddress).maintenance();
        vars.maxLeverageTier = calculateMaximumLeverage(maintenance);

        address token0 = IMarginalV1Pool(vars.poolAddress).token0();
        address token1 = IMarginalV1Pool(vars.poolAddress).token1();
        vars.baseTokenSymbol = safeAssetSymbol(token0);
        vars.quoteTokenSymbol = safeAssetSymbol(token1);

        vars.tokenSize = (!vars.zeroForOne ? token0 : token1);
        vars.tokenDebt = (!vars.zeroForOne ? token1 : token0);

        vars.symbolSize = (
            !vars.zeroForOne ? vars.baseTokenSymbol : vars.quoteTokenSymbol
        );
        vars.symbolDebt = (
            !vars.zeroForOne ? vars.quoteTokenSymbol : vars.baseTokenSymbol
        );

        vars.decimalsSize = safeAssetDecimals(vars.tokenSize);
        vars.decimalsDebt = safeAssetDecimals(vars.tokenDebt);

        // Generate the SVG.
        vars.svg = NFTSVG.generateSVG(
            NFTSVG.SVGParams({
                accentColor: SVGElements.ACCENT_COLOR,
                size: abbreviateAmount({
                    amount: vars.amountSize,
                    decimals: vars.decimalsSize,
                    unit: vars.symbolSize
                }),
                debt: abbreviateAmount({
                    amount: vars.amountDebt,
                    decimals: vars.decimalsDebt,
                    unit: vars.symbolDebt
                }),
                margin: abbreviateAmount({
                    amount: vars.amountMargin,
                    decimals: vars.decimalsSize,
                    unit: vars.symbolSize
                }),
                healthFactor: vars.healthFactor,
                poolAddress: vars.poolAddress.toHexString(),
                poolTicker: generateTicker({
                    quoteTokenSymbol: vars.quoteTokenSymbol,
                    baseTokenSymbol: vars.baseTokenSymbol,
                    maxLeverageTier: vars.maxLeverageTier
                })
            })
        );

        // Generate the JSON metadata.
        vars.json = string.concat(
            '{"description":"',
            generateDescriptionPartOne({
                quoteTokenSymbol: vars.quoteTokenSymbol,
                baseTokenSymbol: vars.baseTokenSymbol,
                poolAddress: vars.poolAddress.toHexString()
            }),
            generateDescriptionPartTwo({
                tokenId: tokenId.toString(),
                baseTokenSymbol: vars.baseTokenSymbol,
                quoteTokenAddress: token1.toHexString(),
                baseTokenAddress: token0.toHexString(),
                maxLeverageTier: vars.maxLeverageTier
            }),
            '","name":"',
            generateName({tokenId: tokenId.toString()}),
            '","image":"data:image/svg+xml;base64,',
            Base64.encode(bytes(vars.svg)),
            '"}'
        );

        // Encode the JSON metadata in Base64.
        return
            string.concat(
                "data:application/json;base64,",
                Base64.encode(bytes(vars.json))
            );
    }

    /*//////////////////////////////////////////////////////////////////////////
                            INTERNAL CONSTANT FUNCTIONS
    //////////////////////////////////////////////////////////////////////////*/

    /// @notice Creates an abbreviated representation of the provided amount, rounded down and prefixed with ">= ".
    /// @dev The abbreviation uses these suffixes:
    /// - "K" for thousands
    /// - "M" for millions
    /// - "B" for billions
    /// - "T" for trillions
    /// For example, if the input is 1,234,567, the output is ">= 1.23M".
    /// @param amount The amount to abbreviate, denoted in units of `decimals`.
    /// @param decimals The number of decimals to assume when abbreviating the amount.
    /// @param unit The unit denomination of the amount.
    /// @return abbreviation The abbreviated representation of the provided amount, as a string.
    function abbreviateAmount(
        uint256 amount,
        uint256 decimals,
        string memory unit
    ) internal pure returns (string memory) {
        string memory units = bytes(unit).length != 0
            ? string.concat(" ", unit)
            : "";
        if (amount == 0) {
            return string.concat("0", units);
        }

        uint256 truncatedAmount;
        uint256 fractionalAmount;
        unchecked {
            truncatedAmount = decimals == 0 ? amount : amount / 10 ** decimals;
            uint256 prod = decimals == 0
                ? amount * 100
                : (amount * 100) / 10 ** decimals;
            fractionalAmount = truncatedAmount < 1000
                ? prod - truncatedAmount * 100
                : 0;
        }

        // Return dummy values when the truncated amount is either very small or very big.
        if (truncatedAmount < 1 && fractionalAmount < 1) {
            return string.concat(SVGElements.SIGN_LT, " 0.01", units);
        } else if (truncatedAmount >= 1e15) {
            return string.concat(SVGElements.SIGN_GT, " 999.99T", units);
        }

        string[5] memory suffixes = ["", "K", "M", "B", "T"];
        uint256 suffixIndex = 0;

        // Truncate repeatedly until the amount is less than 1000.
        unchecked {
            while (truncatedAmount >= 1000) {
                fractionalAmount = (truncatedAmount / 10) % 100; // keep the first two digits after the decimal point
                truncatedAmount /= 1000;
                suffixIndex += 1;
            }
        }

        // Concatenate the calculated parts to form the final string.
        // @dev Removed GTE prefix to show simply truncated number
        string memory wholePart = truncatedAmount.toString();
        string memory fractionalPart = stringifyFractionalAmount(
            fractionalAmount
        );
        return
            string.concat(
                wholePart,
                fractionalPart,
                suffixes[suffixIndex],
                units
            );
    }

    /// @notice Generates a string with the first part of NFT's JSON metadata description, which provides a high-level overview.
    function generateDescriptionPartOne(
        string memory quoteTokenSymbol,
        string memory baseTokenSymbol,
        string memory poolAddress
    ) internal pure returns (string memory) {
        return
            string(
                abi.encodePacked(
                    "This NFT represents a leverage position in a Marginal V1 ",
                    quoteTokenSymbol,
                    "-",
                    baseTokenSymbol,
                    " pool. ",
                    "The owner of this NFT can modify or settle the position.\\n",
                    "\\nPool Address: ",
                    poolAddress,
                    "\\n",
                    quoteTokenSymbol
                )
            );
    }

    /// @notice Generates a string with the second part of NFT's JSON metadata description, which provides a high-level overview.
    function generateDescriptionPartTwo(
        string memory tokenId,
        string memory baseTokenSymbol,
        string memory quoteTokenAddress,
        string memory baseTokenAddress,
        string memory maxLeverageTier
    ) internal pure returns (string memory) {
        return
            string(
                abi.encodePacked(
                    " Address: ",
                    quoteTokenAddress,
                    "\\n",
                    baseTokenSymbol,
                    " Address: ",
                    baseTokenAddress,
                    "\\nMax Leverage Tier: ",
                    maxLeverageTier,
                    "\\nToken ID: ",
                    tokenId,
                    "\\n\\n",
                    unicode"⚠️ DISCLAIMER: Due diligence is imperative when assessing this NFT. Make sure token addresses match the expected tokens, as token symbols may be imitated."
                )
            );
    }

    /// @notice Generates a string with the NFT's JSON metadata name, which is unique for each tokenId.
    function generateName(
        string memory tokenId
    ) internal pure returns (string memory) {
        return string.concat("Marginal V1 Leverage Position #", tokenId);
    }

    /// @notice Geneartes a string with the pool ticker for the NFT's body.
    /// @param quoteTokenSymbol The quote asset symbol of the pool
    /// @param baseTokenSymbol The base asset symbol of the pool
    /// @param maxLeverageTier The maximum leverage of the pool
    /// @return The string representation of the pool ticker
    function generateTicker(
        string memory quoteTokenSymbol,
        string memory baseTokenSymbol,
        string memory maxLeverageTier
    ) internal pure returns (string memory) {
        return
            string.concat(
                baseTokenSymbol,
                "/",
                quoteTokenSymbol,
                " ",
                maxLeverageTier
            );
    }

    /// @notice Retrieves the asset's decimals safely, defaulting to "0" if an error occurs.
    /// @dev Performs a low-level call to handle assets in which the decimals are not implemented.
    function safeAssetDecimals(address asset) internal view returns (uint8) {
        (bool success, bytes memory returnData) = asset.staticcall(
            abi.encodeCall(IERC20Metadata.decimals, ())
        );
        if (success && returnData.length == 32) {
            return abi.decode(returnData, (uint8));
        } else {
            return 0;
        }
    }

    /// @notice Retrieves the asset's symbol safely, defaulting to a hard-coded value if an error occurs.
    /// @dev Performs a low-level call to handle assets in which the symbol is not implemented or it is a bytes32
    /// instead of a string.
    function safeAssetSymbol(
        address asset
    ) internal view returns (string memory) {
        (bool success, bytes memory returnData) = asset.staticcall(
            abi.encodeCall(IERC20Metadata.symbol, ())
        );

        // Non-empty strings have a length greater than 64, and bytes32 has length 32.
        if (!success || returnData.length <= 64) {
            return "ERC20";
        }

        string memory symbol = abi.decode(returnData, (string));

        // The length check is a precautionary measure to help mitigate potential security threats from malicious assets
        // injecting scripts in the symbol string.
        if (bytes(symbol).length > 10) {
            return "Long Symbol";
        } else {
            return symbol;
        }
    }

    /// @notice Calculates the health factor for a position
    /// @param margin The position margin
    /// @param safeMarginMinimum The position safe margin minimum
    /// @return The health factor, as a string
    function calculateHealthFactor(
        uint256 margin,
        uint256 safeMarginMinimum
    ) internal pure returns (string memory) {
        uint256 healthFactor = safeMarginMinimum > 0
            ? (margin * 100) / safeMarginMinimum
            : 0;
        return abbreviateAmount({amount: healthFactor, decimals: 2, unit: ""});
    }

    /// @notice Calculates the maximum leverage for a pool given the maintenance requirement
    /// @param maintenance The maintenance requirement of the pool
    /// @return The string representation of maximum leverage
    function calculateMaximumLeverage(
        uint24 maintenance
    ) internal pure returns (string memory) {
        uint256 leverage = 1e6 + 1e12 / uint256(maintenance);
        return
            string.concat(
                abbreviateAmount({amount: leverage, decimals: 6, unit: ""}),
                "x Max"
            ); // e.g. 5x Max
    }

    /// @notice Converts the provided fractional amount to a string prefixed by a dot.
    /// @param fractionalAmount A numerical value with 2 implied decimals.
    function stringifyFractionalAmount(
        uint256 fractionalAmount
    ) internal pure returns (string memory) {
        // Return the empty string if the fractional amount is zero.
        if (fractionalAmount == 0) {
            return "";
        }
        // Add a leading zero if the fractional part is less than 10, e.g. for "1", this function returns ".01%".
        else if (fractionalAmount < 10) {
            return string.concat(".0", fractionalAmount.toString());
        }
        // Otherwise, stringify the fractional amount simply.
        else {
            return string.concat(".", fractionalAmount.toString());
        }
    }
}
