"""Quiet, native illustrations of capital, reinvestment and strategy discipline.

These are symbolic objects, not charts. Labels and explanations live in HTML;
SVGs remain decorative and each occurrence has its own gradient/filter IDs.
"""
import re


def _defs(prefix):
    return f'''<defs>
      <linearGradient id="{prefix}-ivory" x1="0" y1="0" x2=".8" y2="1">
        <stop stop-color="#fffaf0"/><stop offset="1" stop-color="#d7c9b7"/>
      </linearGradient>
      <linearGradient id="{prefix}-red" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#a1282b"/><stop offset=".42" stop-color="#8b0000"/><stop offset="1" stop-color="#74151b"/>
      </linearGradient>
      <linearGradient id="{prefix}-side" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#bdb09e"/><stop offset="1" stop-color="#958879"/>
      </linearGradient>
      <radialGradient id="{prefix}-light">
        <stop stop-color="#d6bd9d" stop-opacity=".10"/><stop offset="1" stop-color="#d6bd9d" stop-opacity="0"/>
      </radialGradient>
      <filter id="{prefix}-shadow" x="-50%" y="-50%" width="220%" height="220%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="9" result="blur"/>
        <feOffset in="blur" dx="0" dy="13" result="offset"/>
        <feFlood flood-color="#000" flood-opacity=".28" result="ink"/>
        <feComposite in="ink" in2="offset" operator="in" result="shadow"/>
        <feMerge><feMergeNode in="shadow"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <marker id="{prefix}-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="userSpaceOnUse">
        <path d="M1 1L6 4L1 7" fill="none" stroke="#be8883" stroke-width="1.3" stroke-linecap="round"/>
      </marker>
    </defs>'''


def _block(prefix, x, foot, width, height, depth=22, red=False):
    """One architectural block, with three restrained faces."""
    top = foot-height
    shift = depth*.45
    face = f'url(#{prefix}-red)' if red else f'url(#{prefix}-ivory)'
    side = '#611b20' if red else f'url(#{prefix}-side)'
    cap = '#ad3133' if red else '#fff8e9'
    return f'''<g class="scene-block" filter="url(#{prefix}-shadow)">
      <path d="M{x} {top}H{x+width}V{foot}H{x}Z" fill="{face}"/>
      <path d="M{x+width} {top}L{x+width+depth} {top-shift}V{foot-shift}L{x+width} {foot}Z" fill="{side}"/>
      <path d="M{x} {top}L{x+depth} {top-shift}H{x+width+depth}L{x+width} {top}Z" fill="{cap}"/>
      <path d="M{x+1} {top+.5}H{x+width}" fill="none" stroke="#fffaf0" stroke-opacity=".3"/>
    </g>'''


def _coin(prefix, x, y, radius=46, red=False):
    face = f'url(#{prefix}-red)' if red else f'url(#{prefix}-ivory)'
    edge = '#62151b' if red else '#a89a87'
    return f'''<g>
      <path d="M{x-radius} {y}a{radius} 17 0 0 0 {radius*2} 0v8a{radius} 17 0 0 1 {-radius*2} 0Z" fill="{edge}"/>
      <ellipse cx="{x}" cy="{y}" rx="{radius}" ry="17" fill="{face}"/>
      <ellipse cx="{x}" cy="{y}" rx="{radius-8}" ry="12" fill="none" stroke="{'#dda09a' if red else '#b4a28a'}" stroke-opacity=".5"/>
    </g>'''


def _economics(prefix):
    # One business, not a diagram of machinery: retained capital can become
    # a new productive wing. No dimension encodes a measured financial value.
    return f'''
      <ellipse cx="469" cy="313" rx="286" ry="174" fill="url(#{prefix}-light)"/>
      <ellipse cx="456" cy="406" rx="238" ry="23" fill="#000" opacity=".16"/>
      <g data-scene-part="economy">
        {_coin(prefix, 131, 339, 43, True)}
        <path class="scene-flow" d="M182 339C217 339 213 297 250 297" fill="none" stroke="#be8883" stroke-width="1.7" marker-end="url(#{prefix}-arrow)"/>
      </g>
      <g data-scene-part="theory" filter="url(#{prefix}-shadow)">
        <path d="M254 260L278 249H596L572 260Z" fill="#fff8e9"/>
        <path d="M572 260L596 249V384L572 395Z" fill="url(#{prefix}-side)"/>
        <path d="M254 395V279Q254 260 275 260H572V395Z" fill="url(#{prefix}-ivory)"/>
        <path d="M278 395V315Q278 304 289 304H313Q324 304 324 315V395Z" fill="#332a2a"/>
        <path d="M348 395V315Q348 304 359 304H383Q394 304 394 315V395Z" fill="#332a2a"/>
        <path d="M418 395V315Q418 304 429 304H453Q464 304 464 315V395Z" fill="#332a2a"/>
        <path d="M266 271H479" stroke="#fffdf2" stroke-opacity=".55" fill="none"/>
      </g>
      <g data-scene-part="factor" filter="url(#{prefix}-shadow)">
        <path d="M488 395V246Q488 233 500 225L586 178Q601 170 617 178L672 207V395Z" fill="url(#{prefix}-red)"/>
        <path d="M672 207L696 195V384L672 395Z" fill="#65161c"/>
        <path d="M500 225L524 213L609 166Q625 158 641 166L696 195L672 207L617 178Q601 170 586 178Z" fill="#a82f32"/>
        <path d="M507 239L590 194Q601 188 613 194L654 216" fill="none" stroke="#d99185" stroke-opacity=".45" stroke-width="1"/>
        <path d="M515 395V294Q515 270 540 270H620Q646 270 646 294V395Z" fill="#60161b" fill-opacity=".5"/>
        <path d="M534 395V304Q534 289 549 289H611Q627 289 627 304V395Z" fill="#211d1d"/>
      </g>
      <path d="M253 415H696" fill="none" stroke="#d8cbbb" stroke-opacity=".13"/>
    '''


def _endurance(prefix):
    pieces = []
    for x, part in ((132, 'systematic'), (356, 'mean'), (580, 'tails')):
        pieces.append(f'''<g data-scene-part="{part}">
          {_block(prefix, x, 365, 86, 181, 18)}
          <rect x="{x+23}" y="218" width="40" height="86" rx="20" fill="#262020"/>
          <path d="M{x+32} 286H{x+53}" stroke="#a95855" stroke-width="2"/>
          <circle cx="{x+43}" cy="252" r="5" fill="#ac3331"/>
        </g>''')
    return f'''
      <ellipse cx="405" cy="295" rx="298" ry="199" fill="url(#{prefix}-light)"/>
      <path d="M77 399H735" fill="none" stroke="#d8cbbb" stroke-opacity=".13"/>
      {''.join(pieces)}
      <path class="scene-flow" d="M77 356H734" fill="none" stroke="#a33c3b" stroke-width="2" stroke-opacity=".85"/>
      <circle cx="77" cy="356" r="4" fill="#c3756e"/>
      <circle cx="734" cy="356" r="4" fill="#c3756e"/>'''


def _why_now(prefix):
    # Two useful qualities meet in one larger productive business. These forms
    # are deliberately unscaled: neither height nor width encodes a return.
    return f'''
      <ellipse cx="405" cy="299" rx="307" ry="222" fill="url(#{prefix}-light)"/>
      <g data-scene-part="reinvestment">
        {_block(prefix, 158, 208, 57, 73, 16, True)}
        <path d="M170 150H203M170 166H192" fill="none" stroke="#f1c7bc" stroke-opacity=".4"/>
      </g>
      <g data-scene-part="capacity">
        {_block(prefix, 501, 208, 188, 73, 16)}
        <path d="M523 151V192M557 151V192M591 151V192M625 151V192M659 151V192" fill="none" stroke="#ac9b88" stroke-width="1" stroke-opacity=".6"/>
        <rect x="523" y="151" width="34" height="41" fill="#8b0000" opacity=".8"/>
      </g>
      <path class="scene-flow" d="M189 295V331Q189 349 212 349H321M601 295V331Q601 349 578 349H473" fill="none" stroke="#be8883" stroke-width="1.5"/>
      <g data-scene-part="discipline">
        {_block(prefix, 324, 434, 150, 104, 25, True)}
        <path d="M346 355H452M346 377H452M346 399H452M377 350V418M414 350V418" fill="none" stroke="#e2a59b" stroke-opacity=".32" stroke-width="1"/>
        <path d="M309 457H505" fill="none" stroke="#d8cbbb" stroke-opacity=".17"/>
      </g>'''


def objective_scene(kind, uid):
    """Return a decorative SVG with locally scoped IDs and no numerical axes."""
    scenes = {'economics': _economics, 'endurance': _endurance, 'why-now': _why_now}
    if kind not in scenes:
        raise ValueError(f'Unknown objective scene: {kind}')
    prefix = re.sub(r'[^A-Za-z0-9_-]+', '-', str(uid)).strip('-') or 'objective'
    artwork = scenes[kind](prefix).replace('class="scene-flow"', 'class="scene-flow" pathLength="1"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="objective-sculpture" '
            f'viewBox="0 0 800 600" aria-hidden="true" focusable="false" '
            f'data-objective-scene="{kind}">{_defs(prefix)}{artwork}</svg>')
