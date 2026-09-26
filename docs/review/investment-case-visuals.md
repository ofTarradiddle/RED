# Investment case source visuals

Extracted from `DBE Innovation Factor ETF.pptx`, supplied by the user. The source attachment is a PowerPoint, referred to as a PDF in the request. Original chart paths remain unchanged. The business cards use SVG label layers described below; the portfolio-to-REDI sticker has its exterior background removed for transparency.

| Public asset under `assets/investment-case/` | Embedded source | Slide | Placement |
| --- | --- | --- | --- |
| `corporate-metabolism.png` | `ppt/media/image21.png` | 12 | Innovation value slide on homepage and investment case |
| `innovation-research.png` | `ppt/media/image36.png` | 16 | Research following the investment process |
| `innovation-timeline.png` | `ppt/media/image26.png` | 19 | Factor perspective and technology eras |
| `redi-business-card-chart.png` | `ppt/media/image1.png` | 1 | Homepage opening business card with a native Hetzerk header |
| `endogenous-growth.png` | `ppt/media/image19.png` | 7 | Innovation ability slide, with the deck’s title/subtitle restored as native text |
| `portfolio-to-redi-sticker.png` | `ppt/media/image3.png` | 1 | Inline in the homepage Section 351 interest section and both Section 351 page introductions |
| `long-term-characteristics.png` | `ppt/media/image20.png` | 9 | Long-term characteristics section; conceptual return paths, not historical or projected results |
| `portfolio-weighting.png` | `ppt/media/image31.png` | 21 | Portfolio construction slide |
| `factor-comparison.png` | `ppt/media/image37.png` | 13 | Factor comparison chart tab |
| `selection-breadth.png` | `ppt/media/image41.png` | 13 | Selection breadth chart tab |
| `annual-comparison.png` | `ppt/media/image24.png` | 17 | Year-by-year chart tab |

These visuals use the original embedded artwork. The portfolio-to-REDI sticker has only its exterior background removed; the sticker artwork and its colors are retained. It remains a plain inline image, allowing the page background to show around its silhouette without a rectangular backdrop. The other embedded images are unchanged. They contain no Diamond or DBE text. The surrounding page and business-card header use Hetzerk branding.

The charts and timeline retain the source's figures. Their adjacent captions and expanded viewer identify them as backtested strategy research, not actual fund performance or REDI holdings. No figures were transferred into the public ETF performance data. Fee and cost treatment is not specified in the chart, and the supplied research has not been independently verified.

The homepage and ETF backtest cards use `redi-business-card-chart-labeled.svg`
and `redi-business-card-dark-labeled.svg`. Rebuild them with
`python3 scripts/label_redi_backtests.py`. Each self-contained SVG embeds its
unchanged original PNG, masks old text, and supplies native text labels:
**Log returns**, **Innovation Leader**, **Laggard**, and **Market Backtest**.
Market Equal Weight and Non-R&D Payers remain separate series. The heading's
supporting text explicitly identifies the plotted measure as cumulative growth
of $1 on a logarithmic scale; no period log-return data is implied or calculated.
The light card's original CAGR values remain unchanged. The dark card now
distinguishes the navy market series from the teal equal-weight market series.
These SVGs are used in both inline and enlarged views.

The source chart variants have different labels, periods and endpoints; they have not been combined into one data series. The 2026 annual observation is a partial year. The business-card bitmap labels its own date range and backtest status.

Research images can open at full size with keyboard-accessible zoom, and their normal links still work without JavaScript. The portfolio-to-REDI sticker is a plain inline image without a link or viewer. The process tabs display distinct visuals for value, ability and construction; a separate tab group navigates the research time series.

The “Why now” UI expands slide 6 into the five uses of corporate cash and the strategy’s valuation, opportunity, business-exposure and allocation rationale. It omits the undated claim that markets are expensive “today” and the unsupported approximate international-revenue percentage. The long-term characteristics section adapts slide 9’s systematic process, economically supported return hypothesis and portfolio constraints; it does not promise returns or loss protection, or imply that individual positions are held indefinitely.
