"""Editorial research adapted from the supplied innovation-factor draft."""

ARTICLE_ROUTE = 'research/on-innovation-factor-investing.html'
ARTICLE_TITLE = 'Conviction, Measured'
ARTICLE_SUBTITLE = 'An innovation factor built around commercial evidence'
ARTICLE_DESCRIPTION = (
    'A Hetzerk research perspective on commercially successful innovation, '
    'focused factor selection and the evidence an investment signal must earn.'
)
ARTICLE_SECTIONS = (
    ('i-premise', 'The investment question'),
    ('i-evidence', 'From research to results'),
    ('i-measurement', 'Measure the characteristic'),
    ('i-conviction', 'Keep the idea legible'),
    ('i-validation', 'Earn the conviction'),
)


def article_body():
    return '''
      <section id="i-premise" aria-labelledby="i-premise-title">
        <p class="report-section-number">01 / The investment question</p>
        <h2 id="i-premise-title">Where might appreciation come from?</h2>
        <p class="report-lead">A portfolio needs a reason to own its companies, as well as a way to allocate risk among them. Innovation offers a business question to investigate: who can turn investment in knowledge into lasting commercial progress?</p>
        <p>Risk-based portfolio methods address the distribution of exposure. An innovation factor asks what could improve the underlying businesses. These questions belong together: an attractive economic thesis still needs sensible construction, and a sophisticated allocation method does not establish why a company’s earning power should grow.</p>
        <p>Endogenous growth theory provides the economic intuition. Investment in knowledge can expand productive capabilities. At the company level, that suggests looking for businesses that develop and apply useful ideas. It does not prove that innovative stocks will outperform. Commercial value must reach the business, and the share price must leave room for investors to benefit.</p>
      </section>

      <section id="i-evidence" aria-labelledby="i-evidence-title">
        <p class="report-section-number">02 / From research to results</p>
        <h2 id="i-evidence-title">Spending is the input. Success is the question.</h2>
        <p>A large research budget describes commitment, not accomplishment. The proposed innovation measure connects research and development with subsequent business outcomes. The aim is to distinguish firms with evidence of commercial execution from firms whose spending has yet to establish a productive record.</p>
        <figure class="innovation-chain" aria-labelledby="innovation-chain-caption">
          <ol>
            <li><span>01 / Input</span><strong>Research investment</strong><p>What resources went into developing knowledge?</p></li>
            <li><span>02 / Evidence</span><strong>Commercial progress</strong><p>What business results followed that investment?</p></li>
            <li><span>03 / Investment</span><strong>Price &amp; portfolio</strong><p>What are we paying, and what risks are we taking?</p></li>
          </ol>
          <figcaption id="innovation-chain-caption">A research framework; the sequence does not establish causation or forecast returns.</figcaption>
        </figure>
        <p>This changes the starting point for selection. Instead of choosing a technology narrative and finding companies to express it, the process examines company evidence across an eligible universe. Industry exposures emerge from that work. They still need scrutiny: a systematic signal can inherit sector concentrations, accounting differences and the biases of its data.</p>
      </section>

      <section id="i-measurement" aria-labelledby="i-measurement-title">
        <p class="report-section-number">03 / Measure the characteristic</p>
        <h2 id="i-measurement-title">Measure a characteristic. Test its persistence.</h2>
        <p>Measuring a company’s historical ability to commercialize research is different from predicting its next product winner. It gives the model a defined characteristic to estimate and compare across firms. Ranking companies by that estimate lets researchers test whether portfolios at different ranks exhibit different subsequent returns or risks.</p>
        <p>That distinction does not remove forecasting. Selecting stocks still assumes the measured characteristic will remain relevant to future outcomes. Estimates can be noisy or biased; an observed relationship may reflect other business advantages. A more complex model earns its place only if it improves reliable measurement outside the data used to develop it.</p>
        <p>Requiring a commercial history also shapes the opportunity set. It can exclude young firms before their research pays off. That is a deliberate trade-off between evidence and possibility, not proof that established innovators are always better investments.</p>
      </section>

      <section id="i-conviction" aria-labelledby="i-conviction-title">
        <p class="report-section-number">04 / Keep the idea legible</p>
        <h2 id="i-conviction-title">A focused signal, with a reason to exist.</h2>
        <p>We favor a small number of economically motivated signals, each with a clear role in the investment decision. Combining many indicators can diversify estimation errors, but it can also dilute an investment idea or hide overlapping exposures. A focused innovation factor makes the central hypothesis easier to state, test and monitor.</p>
        <p>Focus is not universal optimality. Fewer signals can leave a portfolio more dependent on one mistaken premise. Nor does a focused factor require a concentrated stock portfolio. Selection, weighting, diversification and implementation are separate decisions; each needs evidence appropriate to its role.</p>
      </section>

      <section id="i-validation" aria-labelledby="i-validation-title">
        <p class="report-section-number">05 / Earn the conviction</p>
        <h2 id="i-validation-title">The idea must survive implementation.</h2>
        <p>A credible test begins with information available at each historical decision date, realistic reporting lags and companies that later failed or disappeared. It should compare the signal outside its development sample and examine whether results survive different periods, sectors and reasonable measurement choices.</p>
        <p>The portfolio test must also separate innovation from familiar market and style exposures, account for turnover, trading costs and fund expenses, and explain how missing data and corporate actions are handled. These checks determine whether a research result can support an implementable investment process.</p>
        <aside class="report-callout innovation-takeaway"><strong>The investment perspective</strong><p>Measure commercial ability. Keep the economic idea visible. Require the evidence to survive outside the model. Innovation supplies the hypothesis; disciplined research must earn the conviction.</p></aside>
        <div class="innovation-source">
          <p class="report-source-note">Adapted from “On Innovation Factor Investing,” a Hetzerk research draft.</p>
          <p class="report-source-note">Research perspective, not an individualized recommendation. Equity investments can lose value. Innovation exposure does not guarantee excess returns, diversification benefits or protection against economic risks.</p>
        </div>
      </section>
    '''
