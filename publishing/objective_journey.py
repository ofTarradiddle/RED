"""Native explanations of the deck's economic, durability and allocation arguments.

The diagrams express relationships, not measured returns or forecasts. Original
source exhibits remain available as supporting material rather than the stage.
"""
from html import escape

from publishing.investment_case import case_visual
from publishing.objective_scenes import objective_scene


CHAPTERS = (
    dict(
        key='economics', label='The intuition', subtitle='Innovation belongs inside value',
        kicker='The foundation / Innovation & value',
        title='Innovation<br>belongs in <em>value.</em>',
        body='A business is worth what it can earn over time. Innovation shapes that earning power. Capital allocation determines how the opportunity is pursued.',
        topics=(
            ('theory', 'Value', 'Innovation is part of the business’s value',
             'Better products, processes and capabilities can change future cash flows. Assessing innovation is part of understanding fundamental value, together with risk and the price paid.',
             'What the business earns. What it can become.'),
            ('economy', 'Allocation', 'A separate leadership skill',
             'Operating success does not guarantee capital-allocation skill. Decisions to distribute, reinvest or acquire reach across the business’s future earnings, competitive position and resilience.',
             'Every dollar shapes the business owners hold.'),
            ('factor', 'Reinvestment', 'Create the next source of earnings',
             'Dividends and buybacks return capital to owners. Well-chosen reinvestment in innovation can create new earning power and compound value within the business.',
             'Productive reinvestment can change the whole business.'),
        ),
        anatomy=('Capital allocation', 'Business value', 'Productive reinvestment'),
        takeaway_label='The investment intuition',
        takeaway='Innovation is always part of the value question.<br><strong>We seek the ability to turn it into earning power.</strong>',
        note='The illustration expresses an investment idea, not a forecast. Reinvestment can fail, and even a capable business can be overpriced.',
        source='endogenous', source_label='Economic rationale · Source slide 7',
    ),
    dict(
        key='endurance', label='Investing forever', subtitle='Principles that can endure',
        kicker='What it takes to invest forever',
        title='Principles<br>that <em>endure.</em>',
        body='The businesses change. The question stays: can this remain a sound way to invest through changing markets?',
        topics=(
            ('systematic', 'Repeatable', 'A process beyond the story',
             'Measure the same business characteristic with consistent rules. Holdings evolve as companies change; the discipline should remain understandable and repeatable.',
             'Consistent questions. Consistent decisions.'),
            ('mean', 'Reasoned', 'A reason to expect a return',
             'A lasting strategy needs an economic reason, a coherent theory and evidence that can be challenged. An attractive historical result is only part of the case.',
             'A return expectation supported by more than a sample.'),
            ('tails', 'Resilient', 'Leave room for uncertainty',
             'Ordinary U.S. mid- and large-cap equities, equal weighting and no leverage keep the structure clear. Diversification and disciplined construction help manage risk while leaving room for innovation to disappoint.',
             'Risk discipline. No promise of protection.'),
        ),
        anatomy=('Repeatable process', 'Reasoned expectation', 'Risk discipline'),
        takeaway_label='The portfolio expression',
        takeaway='U.S. mid- &amp; large-cap equities.<br><strong>Equal weight. Long only. No leverage.</strong>',
        note='“Forever” describes the principles, not a permanent holding list. Market losses and company-specific losses remain possible.',
        source='longterm', source_label='Characteristics of fire · Source slide 9',
    ),
    dict(
        key='why-now', label='Why now', subtitle='A rare kind of runway',
        kicker='Why now / The reinvestment opportunity',
        title='Returns.<br>With <em>room.</em>',
        body='High incremental returns matter most when there is room to invest substantial capital. That combination is rare. It is the opportunity we seek.',
        topics=(
            ('reinvestment', 'Returns', 'What can the next dollar earn?',
             'We ask how much additional earning power new investment can create, and whether management has the judgment to pursue it well.',
             'The return on new capital matters.'),
            ('capacity', 'Runway', 'Enough room to matter',
             'A small project can earn exceptional returns and barely move the business. We seek room to reinvest substantial amounts at high incremental returns, repeatedly.',
             'Strong returns. Substantial room to reinvest.'),
            ('discipline', 'Price', 'Own the opportunity at a sensible price',
             'The share price may already reflect an exceptional opportunity. We bring the reinvestment case together with valuation and evidence that the company can execute.',
             'A business opportunity still needs an investment case.'),
        ),
        anatomy=('Attractive new returns', 'Substantial runway', 'Disciplined ownership'),
        takeaway_label='REDI’s selection discipline',
        takeaway='High incremental returns. Room to reinvest.<br><strong>Innovation ability, evaluated through innovation value.</strong>',
        note='This combination is uncommon. Attractive reinvestment opportunities can shrink, execution can fail, and the share price can already reflect the opportunity.',
        source='reinvestment', source_label='Why now · Source slide 6; reinvestment illustration · Slide 12',
    ),
)


def _topics(chapter, stem):
    buttons, panels = [], []
    for index, (key, label, heading, body, principle) in enumerate(chapter['topics'], 1):
        topic_id = f'{stem}-{key}'
        buttons.append(f'''<button type="button" id="{topic_id}-tab" data-objective-topic="{key}" aria-controls="{topic_id}"><span class="objective-topic-index" aria-hidden="true">{index:02}</span><span>{escape(label)}</span></button>''')
        panels.append(f'''<div class="objective-detail" id="{topic_id}" data-objective-detail aria-labelledby="{topic_id}-tab"><h4>{escape(heading)}</h4><p>{escape(body)}</p><div class="objective-principle"><span aria-hidden="true">↳</span>{escape(principle)}</div></div>''')
    return ''.join(buttons), ''.join(panels)


def _hotspots(chapter, stem):
    anchors = {
        'economics': (('economy', 'Capital', 16.3, 80), ('theory', 'Business value', 46, 80), ('factor', 'Reinvestment', 75, 80)),
        'endurance': (('systematic', 'Repeatable', 22, 80), ('mean', 'Reasoned', 50, 80), ('tails', 'Resilient', 78, 80)),
        'why-now': (('reinvestment', 'Incremental returns', 24, 43), ('capacity', 'Reinvestment runway', 75, 43), ('discipline', 'Both, at the right price', 50, 84)),
    }
    return ''.join(f'''<button type="button" class="objective-hotspot" style="--hotspot-x:{x}%;--hotspot-y:{y}%" data-objective-hotspot="{key}" aria-controls="{stem}-{key}" aria-label="Explore {escape(label.lower())}"><span class="objective-hotspot-dot" aria-hidden="true">+</span><span>{label}</span></button>''' for key, label, x, y in anchors[chapter['key']])


def objective_journey(prefix='home'):
    tabs, panels = [], []
    for index, chapter in enumerate(CHAPTERS, 1):
        stem = f'{prefix}-objective-{chapter["key"]}'
        topic_buttons, topic_panels = _topics(chapter, stem)
        tabs.append(f'''<button type="button" id="{stem}-tab" data-objective-tab aria-controls="{stem}"><span class="objective-tab-number" aria-hidden="true">{index:02}</span><span><strong>{chapter['label']}</strong><small>{chapter['subtitle']}</small></span><span class="objective-tab-arrow" aria-hidden="true">↗</span></button>''')
        anatomy = ''.join(f'<span><i aria-hidden="true">{i:02}</i>{label}</span>' for i, label in enumerate(chapter['anatomy'], 1))
        source_extra = ('''<div class="objective-source-context"><h4>The opportunity in context</h4><p>Why now is an ongoing business question: where can the next dollar earn an attractive return, and how much capital can be invested there? Innovation creates possibilities. Capital allocation and valuation determine the investment case.</p></div>''' if chapter['key'] == 'why-now' else '')
        panels.append(f'''<article class="objective-panel objective-{chapter['key']}" id="{stem}" data-objective-panel aria-labelledby="{stem}-tab">
          <div class="objective-exploration" data-objective-exploration data-focus="{chapter['topics'][0][0]}">
            <div class="objective-copy"><p class="objective-kicker"><span aria-hidden="true"></span>{chapter['kicker']}</p>
              <h3>{chapter['title']}</h3><p class="objective-body">{chapter['body']}</p>
              <div class="objective-facets" data-objective-topics aria-label="Explore {escape(chapter['label'].lower())}">{topic_buttons}</div>
              <div class="objective-details">{topic_panels}</div>
            </div>
            <div class="objective-art"><span class="objective-scene-number" aria-hidden="true">{index:02}</span>
              <div class="objective-scene" data-objective-scene>{objective_scene(chapter['key'], stem)}
                <div class="objective-hotspots">{_hotspots(chapter, stem)}</div>
                <div class="objective-scene-heading"><span>{'Capital becomes earning power' if index == 1 else 'Three principles. One discipline.' if index == 2 else 'The rare combination we seek'}</span><small>{'A conceptual relationship · not a forecast' if index != 2 else 'Principles of strategy design'}</small></div>
              </div>
              <div class="objective-anatomy" aria-label="{'Strategy principles' if index == 2 else 'Economic relationships'}">{anatomy}</div>
              <p class="objective-art-hint"><span aria-hidden="true">↖</span> Select {'a quality' if index == 3 else 'a principle' if index == 2 else 'an idea'} to explore the idea</p>
            </div>
          </div>
          <div class="objective-conclusion"><p class="objective-takeaway-label">{chapter['takeaway_label']}</p><p class="objective-takeaway">{chapter['takeaway']}</p><p class="objective-note">{chapter['note']}</p></div>
          <details class="objective-source"><summary><span>Source material <small>{chapter['source_label']}</small></span><span aria-hidden="true">+</span></summary><div class="objective-source-body">{source_extra}{case_visual(chapter['source'], prefix=f'{prefix}-objective-')}</div></details>
        </article>''')
    return f'''<section class="objective-journey" id="{prefix}-objective" data-objective-journey aria-labelledby="{prefix}-objective-title">
      <div class="objective-topline"><h2 id="{prefix}-objective-title">REDI / The investment rationale</h2><a href="/etfs/redi/why-red.html">Full investment case <span aria-hidden="true">↗</span></a></div>
      <div class="objective-navigation"><div class="objective-tabs" data-objective-tabs aria-label="REDI investment rationale">{''.join(tabs)}</div>
        <div class="objective-controls"><span data-objective-count>01 / 03</span><div><button type="button" data-objective-prev aria-label="Previous objective chapter">←</button><button type="button" data-objective-next aria-label="Next objective chapter">→</button></div></div>
      </div>
      <div class="objective-stage" data-objective-stage>{''.join(panels)}</div>
      <span class="objective-status" data-objective-status role="status" aria-live="polite" aria-atomic="true"></span>
    </section>'''
