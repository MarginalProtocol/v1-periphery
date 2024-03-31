// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.19;

import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

import {SVGElements} from "./SVGElements.sol";

/// @title NFTSVG library
/// @author Sablier Labs
/// @notice Generates the SVG image for the Marginal V1 leverage position
/// @dev Fork of Sablier V2 NFTSVG library adapted for Marginal V1 leverage positions
library NFTSVG {
    using Strings for uint256;

    uint256 internal constant CARD_MARGIN = 20;

    struct SVGParams {
        string accentColor;
        string size;
        string debt;
        string margin;
        string healthFactor;
        string poolAddress;
        string poolTicker;
    }

    struct SVGVars {
        string cards;
        uint256 cardsWidth;
        string sizeCard;
        uint256 sizeWidth;
        uint256 sizeXPosition;
        string debtCard;
        uint256 debtWidth;
        uint256 debtXPosition;
        string marginCard;
        uint256 marginWidth;
        uint256 marginXPosition;
        string healthCard;
        uint256 healthWidth;
        uint256 healthXPosition;
    }

    function generateSVG(
        SVGParams memory params
    ) internal pure returns (string memory) {
        SVGVars memory vars;

        // Generate the position size card.
        (vars.sizeWidth, vars.sizeCard) = SVGElements.card({
            cardType: SVGElements.CardType.POSITION_SIZE,
            content: params.size
        });

        // Generate the position debt card.
        (vars.debtWidth, vars.debtCard) = SVGElements.card({
            cardType: SVGElements.CardType.POSITION_DEBT,
            content: params.debt
        });

        // Generate the position margin card.
        (vars.marginWidth, vars.marginCard) = SVGElements.card({
            cardType: SVGElements.CardType.POSITION_MARGIN,
            content: params.margin
        });

        // Generate the position health factor card.
        (vars.healthWidth, vars.healthCard) = SVGElements.card({
            cardType: SVGElements.CardType.HEALTH_FACTOR,
            content: params.healthFactor
        });

        unchecked {
            // Calculate the width of the row containing the cards and the margins between them.
            vars.cardsWidth =
                vars.sizeWidth +
                vars.debtWidth +
                vars.marginWidth +
                vars.healthWidth +
                CARD_MARGIN *
                3;

            // Calculate the positions on the X axis based on the following layout:
            //
            // ______________________ SVG Width (1000px) ________________________
            // |     |      |      |      |      |        |      |        |     |
            // | <-> | Size | 16px | Debt | 16px | Margin | 16px | Health | <-> |
            vars.sizeXPosition = (1000 - vars.cardsWidth) / 2;
            vars.debtXPosition =
                vars.sizeXPosition +
                vars.sizeWidth +
                CARD_MARGIN;
            vars.marginXPosition =
                vars.debtXPosition +
                vars.debtWidth +
                CARD_MARGIN;
            vars.healthXPosition =
                vars.marginXPosition +
                vars.marginWidth +
                CARD_MARGIN;
        }

        // Concatenate all cards.
        vars.cards = string.concat(
            vars.sizeCard,
            vars.debtCard,
            vars.marginCard,
            vars.healthCard
        );

        return
            string.concat(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">',
                SVGElements.BACKGROUND,
                generateLogo(),
                generateDefs(params.accentColor, vars.cards),
                generateFloatingText(params.poolAddress, params.poolTicker),
                generateHrefs(
                    vars.sizeXPosition,
                    vars.debtXPosition,
                    vars.marginXPosition,
                    vars.healthXPosition
                ),
                "</svg>"
            );
    }

    function generateLogo() internal pure returns (string memory) {
        return
            string.concat(
                '<g transform="translate(250,150)" clip-path="url(#clip0_1165_3285)">',
                '<circle opacity="0.6" cx="252.139" cy="290.072" r="85.4106" fill="#FE6C27"/>',
                '<circle opacity="0.9" cx="252.139" cy="290.072" r="68.8003" fill="#FE6C27"/>',
                '<circle cx="252.139" cy="290.072" r="84.9106" stroke="url(#paint201_linear_1165_3285)"/>',
                '<circle opacity="0.2" cx="252.139" cy="290.072" r="155.66" stroke="url(#paint202_linear_1165_3285)"/>',
                '<circle opacity="0.08" cx="252.139" cy="290.072" r="242.005" stroke="url(#paint203_linear_1165_3285)"/>',
                '<path d="M223.222 286.758V271.999L232.929 286.758H239.072L226.836 268.384H217.8V286.758H223.222Z" fill="white"/>',
                '<path d="M223.222 290.373H217.8V295.192H223.222V290.373Z" fill="white"/>',
                '<path d="M223.222 298.807H217.8V311.76H223.222V298.807Z" fill="white"/>',
                '<path d="M240.853 298.807H247.096L252.111 306.338L257.126 298.807H263.367L254.85 311.76H249.371L240.853 298.807Z" fill="white"/>',
                '<path d="M280.604 298.807V311.76H286.026V298.807H280.604Z" fill="white"/>',
                '<path d="M286.026 295.192H280.604V290.373H286.026V295.192Z" fill="white"/>',
                '<path d="M286.026 286.758V268.384H277.385L265.149 286.758H271.289L280.604 272.592V286.758H286.026Z" fill="white"/>',
                '<path d="M268.913 290.373L265.744 295.192H259.533L262.742 290.373H268.913Z" fill="white"/>',
                '<path d="M241.479 290.373H235.306L238.475 295.192H244.689L241.479 290.373Z" fill="white"/>',
                '<path d="M303.347 290.373V295.192H200.932V290.373H303.347Z" fill="white"/>',
                "</g>"
            );
    }

    function generateDefs(
        string memory accentColor,
        string memory cards
    ) internal pure returns (string memory) {
        return
            string.concat(
                "<defs>",
                SVGElements.GLOW,
                SVGElements.NOISE,
                SVGElements.FLOATING_TEXT,
                SVGElements.gradients(accentColor),
                cards,
                "</defs>"
            );
    }

    function generateFloatingText(
        string memory poolAddress,
        string memory poolTicker
    ) internal pure returns (string memory) {
        return
            string.concat(
                '<text text-rendering="optimizeSpeed">',
                SVGElements.floatingText({
                    offset: "-100%",
                    text: string.concat(
                        poolAddress,
                        unicode" • ",
                        "Marginal V1"
                    )
                }),
                SVGElements.floatingText({
                    offset: "0%",
                    text: string.concat(
                        poolAddress,
                        unicode" • ",
                        "Marginal V1"
                    )
                }),
                SVGElements.floatingText({
                    offset: "-50%",
                    text: string.concat(poolAddress, unicode" • ", poolTicker)
                }),
                SVGElements.floatingText({
                    offset: "50%",
                    text: string.concat(poolAddress, unicode" • ", poolTicker)
                }),
                "</text>"
            );
    }

    function generateHrefs(
        uint256 sizeXPosition,
        uint256 debtXPosition,
        uint256 marginXPosition,
        uint256 healthXPosition
    ) internal pure returns (string memory) {
        return
            string.concat(
                '<use href="#Glow" fill-opacity=".9"/>',
                '<use href="#Glow" x="1000" y="1000" fill-opacity=".9"/>',
                '<use href="#Size" x="',
                sizeXPosition.toString(),
                '" y="790"/>',
                '<use href="#Debt" x="',
                debtXPosition.toString(),
                '" y="790"/>',
                '<use href="#Margin" x="',
                marginXPosition.toString(),
                '" y="790"/>',
                '<use href="#Health" x="',
                healthXPosition.toString(),
                '" y="790"/>'
            );
    }
}
