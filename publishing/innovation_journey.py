"""An investment-case exhibit, grounded in the deck's research eras (slide 19).

Dates describe the historical research portfolio, not the firm's history, fund
holdings or dates of invention. Native illustrations are conceptual, not charts.
"""
from html import escape


ERAS = (
    ('digital', '2000–04', '2000', 'Digital rails.',
     'The foundations of a connected world.',
     'Our early research follows web creation, design software and fiber—the foundations of a connected economy.',
     'A new capability needs adoption—and a business that can turn it into cash flow.',
     'Connectivity', 'Digital infrastructure'),
    ('silicon', '2005–09', '2005', 'Silicon & storage.',
     'The building blocks behind the screen.',
     'Chips, storage and graphics processors trace the next chapter of the research, through an unsettled economic cycle.',
     'Innovation develops through cycles. The price paid still matters.',
     'Compute', 'Semiconductors & storage'),
    ('medicine', '2010–14', '2010', 'New ways to live.',
     'Streaming meets precision medicine.',
     'Software scale and advances in medicine broaden the innovation story beyond a single industry.',
     'Scientific progress and commercial success are different tests.',
     'Possibility', 'Software & life sciences'),
    ('cloud', '2015–19', '2015', 'An interconnected stack.',
     'Cloud, AI and the tools that connect them.',
     'Infrastructure, chips and software tools form a connected set of opportunities in the historical research.',
     'Study the business behind the technology: its execution, economics and valuation.',
     'Infrastructure', 'Cloud, AI & tools'),
    ('platforms', '2020–24', '2020', 'Platforms & data.',
     'New connections. New business models.',
     'Payments, digital platforms and infrastructure feature in the research as the ways companies operate continue to change.',
     'A compelling narrative needs evidence of commercial ability.',
     'Connection', 'Platforms & data'),
    ('ai', '2025–26', '2025', 'Intelligence, made physical.',
     'The physical AI stack.',
     'The latest research era, through August 2026, turns to optics, memory and compute—the physical systems behind AI.',
     'Keep the investment lens consistent as the technology changes.',
     'Next chapter', 'Optics, memory & compute'),
)


def _object(name, label, detail):
    return f'''<div class="journey-object">
      <div class="journey-orbit" aria-hidden="true"></div>
      <svg class="journey-sculpture" viewBox="0 0 600 500" aria-hidden="true" focusable="false"><use href="/assets/innovation-objects.svg#journey-{name}"></use></svg>
      <div class="journey-object-label"><span aria-hidden="true"></span><div>{escape(label)}<small>{escape(detail)}</small></div></div>
    </div>'''


def innovation_journey():
    tabs = '<button type="button" id="journey-tab-idea" data-journey-tab aria-controls="journey-panel-idea"><span class="journey-tick" aria-hidden="true"></span><strong>The process</strong><small>A factor lens</small></button>'
    panels = f'''<div id="journey-panel-idea" class="journey-panel journey-introduction" data-journey-panel aria-labelledby="journey-tab-idea">
      <div class="journey-copy">
        <p class="journey-eyebrow"><span> </span>Historical research / Company characteristics</p>
        <h3>A consistent process.<span>Across changing eras.</span></h3>
        <p class="journey-lede">The eras provide context for the historical research. REDI selects companies using innovation value and innovation ability, then equally weights the portfolio.</p>
        <div class="journey-actions"><a class="journey-primary" href="#process">Review the process <span aria-hidden="true">↗</span></a><a class="journey-text-link" data-journey-start href="#journey-panel-digital">Explore the research eras <span aria-hidden="true">↓</span></a></div>
      </div>
      {_object('origin', 'An enduring investment lens', 'Innovation value × innovation ability')}
    </div>'''
    for index, (key, dates, year, heading, subheading, body, lens, label, detail) in enumerate(ERAS, 1):
        tabs += f'''<button type="button" id="journey-tab-{key}" data-journey-tab aria-controls="journey-panel-{key}"><span class="journey-tick" aria-hidden="true"></span><strong>{dates}</strong><small>{escape(detail)}</small></button>'''
        panels += f'''<div id="journey-panel-{key}" class="journey-panel journey-era" data-journey-panel aria-labelledby="journey-tab-{key}">
          <span class="journey-year" aria-hidden="true">{year}</span>
          <div class="journey-copy">
            <p class="journey-eyebrow"><span></span>{dates}{' · Through August 2026' if key == 'ai' else ''} / Research era {index:02}</p>
            <h3>{escape(heading)}</h3>
            <p class="journey-subheading">{escape(subheading)}</p>
            <p class="journey-description">{escape(body)}</p>
            <div class="journey-lens"><span>The investment lens</span><p>{escape(lens)}</p></div>
            <a class="journey-text-link" href="#process">Review the selection process <span aria-hidden="true">↗</span></a>
          </div>
          {_object(key, label, detail)}
        </div>'''
    return f'''<div class="innovation-journey" data-innovation-journey>
      <div class="journey-topline"><span>Hetzerk / Historical research eras</span><a href="/etfs/redi/">Explore REDI <span aria-hidden="true">↗</span></a></div>
      <div class="journey-navigation" id="journey-timeline">
        <div class="journey-navigation-label"><span>Historical context</span><small>Select a research era</small></div>
        <div class="journey-tabs" data-journey-tabs aria-label="Innovation research eras">{tabs}</div>
        <div class="journey-controls"><span data-journey-count>01 / 07</span><button type="button" data-journey-prev aria-label="Previous innovation chapter">←</button><button type="button" data-journey-next aria-label="Next innovation chapter">→</button></div>
      </div>
      <div class="journey-stage" data-journey-stage>{panels}</div>
      <span class="journey-status" data-journey-status role="status" aria-live="polite" aria-atomic="true"></span>
      <div class="journey-source"><p>Eras from the historical research portfolio, 2000–August 2026. Not REDI holdings, allocation themes or actual fund returns.</p><a href="#timeline-source">View the source exhibit <span aria-hidden="true">↗</span></a></div>
    </div>'''
