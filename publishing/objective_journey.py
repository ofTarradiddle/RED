"""The fund's three-part rationale, with unaltered source exhibits."""
from publishing.investment_case import case_visual


CHAPTERS = (
    dict(key='economics', label='Economic foundations', subtitle='Theory, economics & evidence',
         kicker='The economic & theoretical foundation',
         title='The economics<br>of <em>innovation.</em>',
         body='Investment in knowledge can expand a company’s productive possibilities. REDI examines that investment alongside commercial results and the valuation investors pay.',
         points=(('Knowledge', 'Research can create products, processes and capabilities.'),
                 ('Commercial ability', 'The company must turn those capabilities into business value.'),
                 ('Valuation', 'An attractive business still needs a justifiable share price.')),
         visual='endogenous',
         chain=('Research investment', 'Knowledge creation', 'Potential cash flows'),
         note='The economic rationale informs the selection process; it does not establish a guaranteed return.'),
    dict(key='endurance', label='Investing for the long term', subtitle='Principles designed to endure',
         kicker='What it takes to invest forever',
         title='A process designed<br>to <em>endure.</em>',
         body='A durable strategy needs repeatable decisions, an economic reason to invest and explicit portfolio constraints. Those principles guide the process as companies and valuations change.',
         points=(('Systematic decisions', 'Apply consistent measures and selection rules.'),
                 ('Economic rationale', 'Connect innovation with potential future cash flows.'),
                 ('Portfolio discipline', 'Equally weighted, long-only equities without leverage.')),
         visual='longterm',
         chain=('Repeatable process', 'Economic rationale', 'Risk constraints'),
         note='“Forever” describes the intended durability of the principles. Holdings can change, and portfolio constraints do not cap losses.'),
    dict(key='why-now', label='Why now', subtitle='Where capital goes next',
         kicker='Why now / Capital allocation',
         title='Where the next<br><em>dollar goes.</em>',
         body='Companies decide how much cash to return today and how much to invest in tomorrow. REDI studies reinvestment that can create future earning power, with a disciplined view of its value.',
         points=(('Capital allocation', 'Examine where the business directs its next dollar.'),
                 ('Value and ability', 'Assess both the price paid and the capacity to execute.'),
                 ('Changing opportunity', 'Reassess companies as industries and technologies evolve.')),
         visual='reinvestment',
         chain=('Dividends', 'Repurchases', 'Debt repayment', 'Acquisitions', 'Reinvestment'),
         note='The opportunity is assessed company by company. Reinvestment can fail to produce a commercial return.'),
)


def objective_journey(prefix='home'):
    tabs, panels = [], []
    for index, chapter in enumerate(CHAPTERS, 1):
        stem = f'{prefix}-objective-{chapter["key"]}'
        tabs.append(f'''<button type="button" id="{stem}-tab" data-objective-tab aria-controls="{stem}">
          <span class="objective-tab-number" aria-hidden="true">0{index}</span><span><strong>{chapter['label']}</strong><small>{chapter['subtitle']}</small></span><span class="objective-tab-arrow" aria-hidden="true">↗</span>
        </button>''')
        points = ''.join(f'<div><dt>{title}</dt><dd>{text}</dd></div>' for title, text in chapter['points'])
        chain = ''.join(f'<span class="{"is-focus" if chapter["key"] == "why-now" and i == 4 else ""}">{text}</span>' for i, text in enumerate(chapter['chain']))
        panels.append(f'''<article class="objective-panel objective-{chapter['key']}" id="{stem}" data-objective-panel aria-labelledby="{stem}-tab">
          <div class="objective-copy"><span class="objective-watermark" aria-hidden="true">0{index}</span>
            <p class="objective-kicker"><span aria-hidden="true"></span>0{index} / {chapter['kicker']}</p>
            <h3>{chapter['title']}</h3><p class="objective-body">{chapter['body']}</p>
            <dl class="objective-points">{points}</dl>
          </div>
          <div class="objective-exhibit">
            {case_visual(chapter['visual'], prefix=f'{prefix}-objective-', eager=index == 1)}
            <div class="objective-chain{' objective-choices' if chapter['key'] == 'why-now' else ''}" aria-label="{'Five uses of corporate cash' if chapter['key'] == 'why-now' else 'Investment framework'}">{chain}</div>
          </div>
          <p class="objective-note">{chapter['note']}</p>
        </article>''')
    return f'''<section class="objective-journey" id="{prefix}-objective" data-objective-journey aria-labelledby="{prefix}-objective-title">
      <div class="objective-topline"><h2 id="{prefix}-objective-title">The foundations of REDI</h2><a href="/etfs/redi/why-red.html">Full investment case <span aria-hidden="true">↗</span></a></div>
      <div class="objective-navigation"><div class="objective-tabs" data-objective-tabs aria-label="REDI investment objective">{''.join(tabs)}</div>
        <div class="objective-controls"><span data-objective-count>01 / 03</span><div><button type="button" data-objective-prev aria-label="Previous objective chapter">←</button><button type="button" data-objective-next aria-label="Next objective chapter">→</button></div></div>
      </div>
      <div class="objective-stage" data-objective-stage>{''.join(panels)}</div>
      <span class="objective-status" data-objective-status role="status" aria-live="polite" aria-atomic="true"></span>
    </section>'''
