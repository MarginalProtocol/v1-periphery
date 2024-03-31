// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.19;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @title SVGElements library
/// @author Sablier Labs
/// @notice Generates SVG elements for the Marginal V1 leverage position
/// @dev Fork of Sablier V2 SVGElements library addapted for Marginal V1 leverage positions
library SVGElements {
    using Strings for string;
    using Strings for uint256;

    /*//////////////////////////////////////////////////////////////////////////
                                     CONSTANTS
    //////////////////////////////////////////////////////////////////////////*/

    string internal constant BACKGROUND =
        '<rect width="100%" height="100%" filter="url(#Noise)"/><rect x="70" y="70" width="860" height="860" fill="#fff" fill-opacity=".03" rx="45" ry="45" stroke="#fff" stroke-opacity=".1" stroke-width="4"/>';

    string internal constant BACKGROUND_COLOR = "hsl(0,0%,10%)";

    string internal constant ACCENT_COLOR = "hsl(19,99%,57%)";

    string internal constant FLOATING_TEXT =
        '<path id="FloatingText" fill="none" d="M125 45h750s80 0 80 80v750s0 80 -80 80h-750s-80 0 -80 -80v-750s0 -80 80 -80"/>';

    string internal constant GLOW =
        '<circle id="Glow" r="500" fill="url(#RadialGlow)"/>';

    string internal constant NOISE =
        '<filter id="Noise"><feFlood x="0" y="0" width="100%" height="100%" flood-color="hsl(0,0%,10%)" flood-opacity="1" result="floodFill"/><feTurbulence baseFrequency=".4" numOctaves="3" result="Noise" type="fractalNoise"/><feBlend in="Noise" in2="floodFill" mode="soft-light"/></filter>';

    /// @dev Escape character for "≥".
    string internal constant SIGN_GE = "&#8805;";

    /// @dev Escape character for ">".
    string internal constant SIGN_GT = "&gt;";

    /// @dev Escape character for "<".
    string internal constant SIGN_LT = "&lt;";

    /*//////////////////////////////////////////////////////////////////////////
                                     DATA TYPES
    //////////////////////////////////////////////////////////////////////////*/

    enum CardType {
        POSITION_SIZE,
        POSITION_DEBT,
        POSITION_MARGIN,
        HEALTH_FACTOR
    }

    /*//////////////////////////////////////////////////////////////////////////
                                     COMPONENTS
    //////////////////////////////////////////////////////////////////////////*/

    function card(
        CardType cardType,
        string memory content
    ) internal pure returns (uint256 width, string memory card_) {
        string memory caption = stringifyCardType(cardType);

        // The width is calculated dynamically based on the number of characters.
        uint256 captionWidth = calculatePixelWidth({
            text: caption,
            largeFont: false
        });
        uint256 contentWidth = calculatePixelWidth({
            text: content,
            largeFont: false
        });

        // Use the greater of the two widths, and add the left and the right margin.
        unchecked {
            width = Math.max(captionWidth, contentWidth) + 40;
        }

        card_ = string.concat(
            '<g id="',
            caption,
            '" fill="#fff">',
            '<rect width="',
            width.toString(),
            '" height="100" fill-opacity=".03" rx="15" ry="15" stroke="#fff" stroke-opacity=".1" stroke-width="4"/>',
            '<text x="20" y="34" font-family="\'Courier New\',Arial,monospace" font-size="22px">',
            caption,
            "</text>",
            '<text x="20" y="72" font-family="\'Courier New\',Arial,monospace" font-size="22px">',
            content,
            "</text>",
            "</g>"
        );
    }

    function floatingText(
        string memory offset,
        string memory text
    ) internal pure returns (string memory) {
        return
            string.concat(
                '<textPath startOffset="',
                offset,
                '" href="#FloatingText" fill="#fff" font-family="\'Courier New\',Arial,monospace" fill-opacity=".8" font-size="26px">',
                '<animate additive="sum" attributeName="startOffset" begin="0s" dur="50s" from="0%" repeatCount="indefinite" to="100%"/>',
                text,
                "</textPath>"
            );
    }

    function gradients(
        string memory accentColor
    ) internal pure returns (string memory) {
        return
            string.concat(
                '<radialGradient id="RadialGlow">',
                '<stop offset="0%" stop-color="',
                accentColor,
                '" stop-opacity=".6"/>',
                '<stop offset="100%" stop-color="',
                BACKGROUND_COLOR,
                '" stop-opacity="0"/>',
                "</radialGradient>"
            );
    }

    /*//////////////////////////////////////////////////////////////////////////
                                      HELPERS
    //////////////////////////////////////////////////////////////////////////*/

    /// @notice Calculates the pixel width of the provided string.
    /// @dev Notes:
    /// - A factor of ~0.6 is applied to the two font sizes used in the SVG (26px and 22px) to approximate the average
    /// character width.
    /// - It is assumed that escaped characters are placed at the beginning of `text`.
    /// - It is further assumed that there is no other semicolon in `text`.
    function calculatePixelWidth(
        string memory text,
        bool largeFont
    ) internal pure returns (uint256 width) {
        uint256 length = bytes(text).length;
        if (length == 0) {
            return 0;
        }

        unchecked {
            uint256 charWidth = largeFont ? 16 : 13;
            uint256 semicolonIndex;
            for (uint256 i = 0; i < length; ) {
                if (bytes(text)[i] == ";") {
                    semicolonIndex = i;
                }
                width += charWidth;
                i += 1;
            }

            // Account for escaped characters (such as &#8805;).
            width -= charWidth * semicolonIndex;
        }
    }

    /// @notice Retrieves the card type as a string.
    function stringifyCardType(
        CardType cardType
    ) internal pure returns (string memory) {
        if (cardType == CardType.POSITION_SIZE) {
            return "Size";
        } else if (cardType == CardType.POSITION_DEBT) {
            return "Debt";
        } else if (cardType == CardType.POSITION_MARGIN) {
            return "Margin";
        } else {
            return "Health";
        }
    }
}
