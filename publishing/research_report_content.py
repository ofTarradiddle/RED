"""Source-grounded research article adapted from the supplied strategy deck."""

from publishing.investment_case import case_visual


REPORT_TITLE = 'The Measure of Fire'
REPORT_SUBTITLE = 'Innovation as an equity factor'
REPORT_DESCRIPTION = (
    'Hetzerk research on innovation value, commercial ability and systematic '
    'equity selection, with original strategy figures and a clear account of '
    'the evidence and its limits.'
)


def report_body():
    """Return article content for the themed web report and its print edition."""
    return f'''
      <section id="r-summary" aria-labelledby="r-summary-title">
        <p class="report-section-number">01 / Executive summary</p>
        <h2 id="r-summary-title">A business characteristic worth measuring.</h2>
        <p class="report-lead">Innovation becomes an investment proposition when a company can turn research into a commercial result—and when the price of its shares leaves room for that result to reward investors.</p>
        <p>The research behind the Hetzerk Innovation Factor ETF, REDI, combines two questions: what are investors paying for a company’s innovation activity, and how capable is that company of converting it into business value? The intended approach selects U.S. mid- and large-cap equities systematically and equally weights the selected companies. Its objective is long-term capital appreciation through equity ownership, without leverage.</p>
        <p>This report develops the economic rationale, outlines the investment process and examines the historical research. The exhibits support a hypothesis about innovation and equity returns; they do not establish a verified return premium. All performance figures below are backtested strategy research, not actual ETF performance.</p>
      </section>

      <section id="r-rationale" aria-labelledby="r-rationale-title">
        <p class="report-section-number">02 / Economic rationale</p>
        <h2 id="r-rationale-title">From research spending to shareholder value.</h2>
        <p>The economic starting point is endogenous growth: investment in knowledge can expand a business’s productive possibilities. Applied to companies, the proposition is that research may create products, improve existing processes or establish capabilities that competitors cannot immediately reproduce. Those outcomes can change future cash flows. Research spending is an input to that process; it is not proof of a successful outcome.</p>
        <p>There are two further steps between useful invention and attractive equity returns. A company must capture an economic benefit from its work, and investors must pay a price that does not already assume too much success. An important technology can benefit customers while generating disappointing returns for its producers. A successful business can also be an unattractive investment at an excessive valuation.</p>
        <p>This is the rationale for measuring innovation as a company characteristic. The proposed factor follows evidence about firms across changing technologies, rather than requiring a fixed allocation to one industry narrative. The deck’s historical comparisons are consistent with that idea, but cannot by themselves show whether observed returns reflect a distinct innovation premium, other equity exposures or choices made during model development.</p>
      </section>

      <section id="r-process" aria-labelledby="r-process-title">
        <p class="report-section-number">03 / The proposed process</p>
        <h2 id="r-process-title">Innovation value. Innovation ability.</h2>
        <p><strong>Innovation value</strong> asks whether the price paid is justified by the company’s innovation activity. The deck describes this as innovation at a justifiable valuation. The investment question is broader than whether a stock looks inexpensive on a conventional ratio: what future business results might its research support, and how much of that possibility is already reflected in the valuation?</p>
        <p><strong>Innovation ability</strong> asks whether a company can use its research effectively. A record of commercial execution can help distinguish purposeful investment from spending without a convincing business result. The intended signal concerns the company’s capacity to innovate, not merely the size of its research budget. That distinction is central to the thesis, although the deck does not provide an executable definition of the ability measure.</p>
        <div class="report-table-wrap"><table>
          <caption>The selection sequence described in the presentation</caption>
          <thead><tr><th scope="col">Stage</th><th scope="col">Investment question</th><th scope="col">Proposed action</th></tr></thead>
          <tbody>
            <tr><th scope="row">Innovation value</th><td>Is the innovation opportunity reasonably priced?</td><td>Select a subset of the U.S. mid- and large-cap universe.</td></tr>
            <tr><th scope="row">Innovation ability</th><td>Can the company turn research into commercial progress?</td><td>Narrow the selection using the ability measure.</td></tr>
            <tr><th scope="row">Portfolio construction</th><td>How should selected companies share the allocation?</td><td>Equally weight the selected equities.</td></tr>
          </tbody>
        </table></div>
        <p>Equal weighting gives each selected company the same target allocation at a rebalance. It makes the selection decision consequential without assigning the largest positions simply to the largest companies. It also introduces its own exposures and trading requirements. The deck’s weighting appendix compares equal weighting, inverse-volatility weighting and risk parity under specified assumptions; it does not demonstrate that one rule is always superior.</p>
        <p class="report-source-note">Process source: slides 10 and 21 of the strategy presentation. The supplied materials do not specify final selection counts, complete signal formulas or all implementation rules. The sequence above describes the framework rather than an executable portfolio specification.</p>
      </section>

      <section id="r-evidence" aria-labelledby="r-evidence-title">
        <p class="report-section-number">04 / Empirical evidence</p>
        <h2 id="r-evidence-title">Read the path as well as the endpoint.</h2>
        <p>Slide 16 presents six research series using September 2002 as a common $1 starting value, with monthly observations through August 2026. The source labels its two innovation variants “Pred Innovation” and “Innovation.” Their displayed endpoints are 77.35× and 59.55×, respectively. The other series end at 18.41× for “R&amp;D Other,” 15.52× for “Market EW,” 15.02× for “Market” and 12.54× for “Non-payers.” These are chart labels, not independently reproduced results.</p>
        {case_visual('research', prefix='r-')}
        <p>The absolute scale makes the ending wealth differences visible. The logarithmic scale and first-decade inset show that the path includes substantial declines and periods when the series are much closer together. A persuasive investment case needs both views: an attractive final value does not explain how difficult the strategy would have been to hold, or whether its advantage survived realistic implementation costs.</p>
        <p>The annual comparison on slide 17 provides another perspective. In its figure, Innovation is labelled −40.0% in 2008 versus −37.0% for the S&amp;P 500; +81.7% in 2009 versus +26.5%; and −23.4% in 2022 versus −18.1%. In 2024, both series are positive, but Innovation’s +21.4% trails the comparison’s +25.0%. These observations illustrate both large gains and meaningful relative or absolute losses. They do not establish downside protection.</p>
        {case_visual('annual', prefix='r-')}
        <p class="report-source-note">The annual figure spans 2003–2026; 2026 is a partial year. Its benchmark label is “S&amp;P 500,” while the separate native table on the same slide uses “MKT” and different comparison values. The figures also differ from other research variants in the deck. They are retained as distinct source exhibits, not combined into one audited track record. Benchmark definitions, return conventions, fees and trading-cost treatment need reconciliation.</p>
      </section>

      <section id="r-why-now" aria-labelledby="r-why-now-title">
        <p class="report-section-number">05 / Why now</p>
        <h2 id="r-why-now-title">Follow the next dollar of reinvestment.</h2>
        <p>The opportunity begins with a capital-allocation question. A company can return cash through dividends or repurchases, repay debt, acquire another business, or reinvest internally. REDI’s research focuses on the last of these: spending that may change the company’s future earning power.</p>
        <p>Cash returned to shareholders and cash retained for innovation answer different investment questions. Reinvestment deserves scrutiny because its payoff can arrive late, remain uncertain or fail altogether. The proposed value-and-ability framework seeks to evaluate both the opportunity and the company’s capacity to pursue it. A growing research budget alone cannot establish either.</p>
        <p>The presentation connects innovation with changing industries and with U.S. companies that serve customers abroad. Overseas revenue can broaden a business’s economic exposure, but does not turn a U.S. equity portfolio into an international equity allocation. Likewise, the deck’s assertion that innovation may be discounted is a hypothesis to test company by company. Without current valuation and holdings data, it is not evidence of a market-wide opportunity today.</p>
      </section>

      <section id="r-durability" aria-labelledby="r-durability-title">
        <p class="report-section-number">06 / Durable characteristics</p>
        <h2 id="r-durability-title">A repeatable process for a changing market.</h2>
        <p>The deck’s phrase “a portfolio you can hold forever” describes desired characteristics of a strategy: systematic decisions, an economic reason to expect a return, and risk constraints in portfolio construction. It does not mean every security should be held indefinitely. Companies can lose their innovative advantage, valuations can become demanding, and new candidates can emerge.</p>
        <p>Systematic selection makes decisions reviewable. The economic rationale gives researchers something to test beyond a fitted return history. Long-only equities, equal weighting and the absence of leverage define the intended construction. These choices do not eliminate market losses, sector concentration or the possibility that several holdings respond to the same underlying risk.</p>
        <p>The deck proposes consideration within either a core or satellite equity allocation. Assessing that role requires evidence about holdings overlap, sector exposures, volatility and behavior alongside an investor’s other assets. A distinct selection rule does not necessarily create a distinct source of portfolio risk.</p>
      </section>

      <section id="r-validation" aria-labelledby="r-validation-title">
        <p class="report-section-number">07 / Research limitations</p>
        <h2 id="r-validation-title">What would make the evidence reproducible?</h2>
        <p>Reproducibility requires a fixed, testable specification: defined valuation and ability formulas, final selection counts, a documented eligible universe, and explicit rebalance, data-lag and corporate-action rules. These inputs need to accompany the underlying observations before the historical strategy can be independently reconstructed.</p>
        <p>A reproducible dataset must preserve what was known at each decision date, including companies that later disappeared. Researchers should reconcile the deck’s variants against their underlying holdings and return series, identify each benchmark, and disclose dividend and fee treatment. Net results should reflect the fund’s expense ratio and realistic turnover, spreads and trading costs. The supplied materials do not establish that these costs are included.</p>
        <p>Validation should then test sensitivity to selection breadth and measurement choices, examine results outside model development, and separate innovation exposure from conventional market, size, sector and style effects. These checks determine whether the economic idea survives implementation. Until then, the evidence remains an encouraging research record with material unresolved assumptions, rather than a verified forecast of investor outcomes.</p>
        <aside class="report-callout"><strong>Research perspective</strong><p>Innovation can be an economically meaningful company characteristic. The investment case depends on measuring it consistently, paying a justifiable price and demonstrating that the resulting portfolio works under realistic conditions.</p></aside>
      </section>

      <section id="r-sources" aria-labelledby="r-sources-title">
        <p class="report-section-number">08 / Source notes</p>
        <h2 id="r-sources-title">About this report.</h2>
        <p>This report adapts the supplied Innovation Factor ETF strategy presentation for Hetzerk Asset Management. Slide references follow that presentation’s order. The report does not independently verify its underlying data.</p>
        <ul class="report-sources">
          <li><strong>Thesis and rationale:</strong> slides 4, 7, 8 and 10.</li>
          <li><strong>Reinvestment and timing argument:</strong> slides 6, 11 and 12.</li>
          <li><strong>Historical evidence:</strong> slides 13–17; reproduced figures from slides 16 and 17.</li>
          <li><strong>Durable characteristics and construction:</strong> slides 9, 10 and 21.</li>
        </ul>
        <p class="report-source-note">Backtested performance is hypothetical, is subject to model and data limitations, and does not represent actual fund returns. Past performance does not guarantee future results. Equity investments can lose value. This research report is not a prospectus or an individualized investment recommendation.</p>
      </section>
    '''
