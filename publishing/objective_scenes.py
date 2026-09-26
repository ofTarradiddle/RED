"""Native, text-free diagrams for the immersive investment-objective chapter.

The surrounding HTML owns descriptions, labels and controls. These SVGs are
decorative conceptual diagrams; their paths do not encode investment returns.
"""

import math
import re


def _defs(prefix):
    return f'''<defs>
      <linearGradient id="{prefix}-ceramic" x1="0" y1="0" x2=".9" y2="1">
        <stop stop-color="#fffdf7"/><stop offset=".52" stop-color="#f2e8dd"/><stop offset="1" stop-color="#d7c3b3"/>
      </linearGradient>
      <linearGradient id="{prefix}-edge" x1="0" y1="0" x2="0" y2="1">
        <stop stop-color="#d9bdab"/><stop offset=".48" stop-color="#b98f76"/><stop offset="1" stop-color="#ede0d2"/>
      </linearGradient>
      <linearGradient id="{prefix}-copper" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#ead2bc"/><stop offset=".42" stop-color="#a47359"/><stop offset=".7" stop-color="#cfa68a"/><stop offset="1" stop-color="#82533f"/>
      </linearGradient>
      <linearGradient id="{prefix}-oxblood" x1="0" y1="0" x2=".8" y2="1">
        <stop stop-color="#b9332d"/><stop offset=".48" stop-color="#8b0000"/><stop offset="1" stop-color="#580f18"/>
      </linearGradient>
      <linearGradient id="{prefix}-glaze" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#fffdf9" stop-opacity=".74"/><stop offset="1" stop-color="#fffdf9" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="{prefix}-glass" x1="0" y1="0" x2="1" y2=".3">
        <stop stop-color="#fffcf4" stop-opacity=".56"/><stop offset=".45" stop-color="#e1d0bd" stop-opacity=".1"/><stop offset="1" stop-color="#c7a991" stop-opacity=".25"/>
      </linearGradient>
      <radialGradient id="{prefix}-pearl" cx=".3" cy=".23" r=".8">
        <stop stop-color="#fffef8"/><stop offset=".55" stop-color="#e7d4c0"/><stop offset="1" stop-color="#ac8166"/>
      </radialGradient>
      <radialGradient id="{prefix}-ground">
        <stop stop-color="#754b36" stop-opacity=".16"/><stop offset="1" stop-color="#754b36" stop-opacity="0"/>
      </radialGradient>
      <filter id="{prefix}-cast" x="-50%" y="-60%" width="200%" height="230%">
        <feDropShadow dx="1" dy="12" stdDeviation="10" flood-color="#613b29" flood-opacity=".17"/>
      </filter>
      <filter id="{prefix}-close" x="-50%" y="-70%" width="200%" height="250%">
        <feDropShadow dx="0" dy="5" stdDeviation="4" flood-color="#553122" flood-opacity=".18"/>
      </filter>
      <marker id="{prefix}-red-arrow" markerWidth="9" markerHeight="9" refX="6.5" refY="4.5" orient="auto" markerUnits="userSpaceOnUse">
        <path d="M1 1L7 4.5L1 8" fill="none" stroke="#8b0000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </marker>
      <marker id="{prefix}-copper-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="userSpaceOnUse">
        <path d="M1 1L6 4L1 7" fill="none" stroke="#a77b60" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
      </marker>
    </defs>'''


def _disc(prefix, x, y, rx=50, ry=23, red=False, depth=11):
    """A turned ceramic/copper plinth in a common oblique perspective."""
    top = f'url(#{prefix}-oxblood)' if red else f'url(#{prefix}-ceramic)'
    edge = '#67151b' if red else f'url(#{prefix}-edge)'
    return f'''<g filter="url(#{prefix}-close)">
      <path d="M{x-rx} {y} a{rx} {ry} 0 0 0 {rx*2} 0 v{depth} a{rx} {ry} 0 0 1 {-rx*2} 0Z" fill="{edge}"/>
      <ellipse cx="{x}" cy="{y+depth}" rx="{rx}" ry="{ry}" fill="none" stroke="#8b5c47" stroke-opacity=".34"/>
      <ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{top}" stroke="#fffaf1" stroke-opacity=".85"/>
      <ellipse cx="{x}" cy="{y-1}" rx="{rx-7}" ry="{max(ry-5, 4)}" fill="none" stroke="{'#f6b3a0' if red else '#b08b70'}" stroke-opacity=".36"/>
    </g>'''


def _bead(prefix, x, y, radius=5, red=False):
    fill = f'url(#{prefix}-oxblood)' if red else f'url(#{prefix}-pearl)'
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="#fff9ef" stroke-width=".8"/>'


def _economics(prefix):
    # The knowledge cloud has repeated connections, rather than a single funnel.
    nodes = [
        (278, 174), (318, 124), (375, 100), (431, 113), (475, 153),
        (489, 204), (450, 242), (394, 250), (337, 230), (304, 203),
        (350, 170), (397, 150), (434, 183), (391, 210),
    ]
    links = [(0, 1), (0, 9), (0, 10), (1, 2), (1, 10), (1, 11),
             (2, 3), (2, 11), (3, 4), (3, 11), (3, 12), (4, 5),
             (4, 12), (5, 6), (5, 12), (6, 7), (6, 12), (6, 13),
             (7, 8), (7, 13), (8, 9), (8, 10), (8, 13), (9, 10),
             (10, 11), (10, 13), (11, 12), (11, 13), (12, 13),
             (0, 8), (1, 8), (2, 4), (3, 5), (7, 9)]
    cloud = []
    for a, b in links:
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        cloud.append(f'<path d="M{x1} {y1} Q{(x1+x2)/2:.1f} {(y1+y2)/2-10:.1f} {x2} {y2}" fill="none" stroke="#ad866c" stroke-opacity=".43" stroke-width="1.15"/>')
    cloud.extend(_bead(prefix, x, y, 4.2 if i < 10 else 6.1, i in (2, 6, 10)) for i, (x, y) in enumerate(nodes))
    return f'''
      <ellipse cx="403" cy="450" rx="328" ry="61" fill="url(#{prefix}-ground)"/>
      <g data-scene-part="economy">
        <path d="M155 359C232 419 302 404 395 344" fill="none" stroke="#b3957c" stroke-opacity=".14" stroke-width="19"/>
        <path d="M155 350C232 411 302 396 395 335" fill="none" stroke="url(#{prefix}-copper)" stroke-width="13" stroke-linecap="round"/>
        <path d="M165 347C237 399 306 386 379 340" fill="none" stroke="#fffaf2" stroke-opacity=".77" stroke-width="1.3"/>
        <path class="scene-flow" d="M206 374C254 395 301 385 336 367" fill="none" stroke="#8b0000" stroke-width="2" marker-end="url(#{prefix}-red-arrow)"/>
        {_disc(prefix, 155, 368, 77, 34, depth=17)}
        <g filter="url(#{prefix}-cast)">
          <path d="M111 334L155 314L198 334L154 355Z" fill="url(#{prefix}-ceramic)" stroke="#fffdf7"/>
          <path d="M111 334V353L154 374V355Z" fill="#d3b9a3" stroke="#c6a58d" stroke-width=".7"/>
          <path d="M154 355L198 334V352L154 374Z" fill="url(#{prefix}-edge)"/>
          <path d="M119 321L155 304L190 321L155 338Z" fill="url(#{prefix}-ceramic)" stroke="#fffdf7"/>
          <path d="M119 321V331L155 350V338Z" fill="#dac4af"/>
          <path d="M155 338L190 321V332L155 350Z" fill="#b98e73"/>
          <path d="M132 307L155 296L178 307L155 319Z" fill="url(#{prefix}-oxblood)" stroke="#dc9b82" stroke-width=".7"/>
          <path d="M132 307V314L155 326L178 315V307L155 319Z" fill="#74131a"/>
        </g>
        <path d="M125 495C122 462 146 438 155 401" fill="none" stroke="url(#{prefix}-copper)" stroke-width="4" stroke-linecap="round" marker-end="url(#{prefix}-copper-arrow)"/>
        {_disc(prefix, 124, 497, 36, 13, depth=7)}
        {_disc(prefix, 124, 487, 31, 11, depth=5)}
        <ellipse cx="124" cy="486" rx="21" ry="6.8" fill="none" stroke="#a37459" stroke-opacity=".5"/>
      </g>
      <g data-scene-part="theory">
        <path d="M155 313C192 235 208 190 278 174" fill="none" stroke="#ac8266" stroke-width="1.5" stroke-opacity=".65"/>
        <path d="M178 309C231 289 245 256 304 203" fill="none" stroke="#ac8266" stroke-width="1.4" stroke-opacity=".4"/>
        <path d="M397 254V299" fill="none" stroke="#ad826a" stroke-width="1.3"/>
        <path d="M337 230C329 274 338 309 371 333M450 242C463 288 451 314 423 335" fill="none" stroke="#b58e73" stroke-width="1.2" stroke-opacity=".53"/>
        {''.join(cloud)}
        <path class="scene-flow" d="M350 170C373 156 382 150 397 150C416 154 425 169 434 183C446 207 433 229 450 242" fill="none" stroke="#8b0000" stroke-width="2" stroke-opacity=".85"/>
        {_disc(prefix, 395, 364, 94, 41, depth=18)}
        {_disc(prefix, 395, 344, 74, 32, depth=12)}
        <ellipse cx="395" cy="341" rx="43" ry="18" fill="#dcc4af" stroke="#b98b6e" stroke-width=".8"/>
        <ellipse cx="395" cy="338" rx="35" ry="14" fill="url(#{prefix}-oxblood)" stroke="#d18673" stroke-width="1"/>
        <path d="M367 337C380 326 407 326 421 337" fill="none" stroke="#f4be9f" stroke-width=".9" stroke-opacity=".8"/>
        {_bead(prefix, 395, 303, 8.5, True)}
        <path d="M395 313V326" stroke="#8b0000" stroke-width="1.7"/>
      </g>
      <g data-scene-part="factor">
        <path d="M443 346C491 370 545 375 596 357" fill="none" stroke="#8b4f3b" stroke-opacity=".14" stroke-width="18"/>
        <path d="M443 338C493 361 545 368 600 347" fill="none" stroke="url(#{prefix}-oxblood)" stroke-width="11" stroke-linecap="round"/>
        <path d="M448 335C498 358 549 362 592 346" fill="none" stroke="#f7b99d" stroke-opacity=".75" stroke-width="1.2"/>
        <path d="M478 242C549 220 576 199 616 186M489 204C550 173 594 145 670 157M471 294C552 294 585 274 636 263M466 332C535 323 589 314 690 305" fill="none" stroke="#b49a85" stroke-width="1.2" stroke-opacity=".43"/>
        <path class="scene-flow" d="M450 242C532 214 558 242 600 347M489 204C555 198 610 232 646 314" fill="none" stroke="#8b0000" stroke-width="2.2" stroke-opacity=".9"/>
        {_bead(prefix, 616, 186, 5)}{_bead(prefix, 670, 157, 4.5)}{_bead(prefix, 636, 263, 5)}{_bead(prefix, 690, 305, 5)}
        {_disc(prefix, 646, 368, 77, 34, depth=17)}
        <path d="M608 334L646 314L684 334V358L646 381L608 358Z" fill="url(#{prefix}-oxblood)" stroke="#8b191c" filter="url(#{prefix}-close)"/>
        <path d="M608 334L646 314L684 334L646 355Z" fill="url(#{prefix}-ceramic)" stroke="#fffaf0"/>
        <path d="M646 355V379M610 337L642 355" fill="none" stroke="#efa987" stroke-opacity=".45" stroke-width=".9"/>
        <path d="M630 332L646 324L662 332L646 340Z" fill="url(#{prefix}-copper)" stroke="#fff4e2" stroke-width=".8"/>
      </g>'''


def _gate(prefix, x, height, part, front=False):
    top, bottom = 452-height, 452
    if front:
        return f'''<g data-scene-part="{part}" opacity=".82">
          <path d="M{x-17} {top+7}V{bottom-2}L{x-5} {bottom+5}V{top+14}Z" fill="url(#{prefix}-glaze)" stroke="#fff9ed" stroke-width="1"/>
          <path d="M{x-17} {top+7}L{x+20} {top-8}L{x+31} {top-1}" fill="none" stroke="#fffcf4" stroke-width="1.5"/>
          <path d="M{x-5} {bottom+5}L{x+29} {bottom-9}" fill="none" stroke="#bba089" stroke-width="1.1"/>
        </g>'''
    return f'''<g data-scene-part="{part}">
      <ellipse cx="{x+5}" cy="467" rx="52" ry="15" fill="url(#{prefix}-ground)"/>
      <path d="M{x-24} 447L{x+24} 428L{x+47} 441L{x-1} 462Z" fill="url(#{prefix}-ceramic)" stroke="#fffaf0"/>
      <path d="M{x-24} 447V455L{x-1} 469L{x+47} 449V441L{x-1} 462Z" fill="url(#{prefix}-edge)"/>
      <path d="M{x-17} {bottom}V{top+7}L{x+20} {top-8}L{x+31} {top-1}V{bottom-14}L{x+20} {bottom-7}V{top+14}L{x-5} {top+24}V{bottom+5}Z" fill="url(#{prefix}-glass)" stroke="#c8ac93" stroke-width="1.05"/>
      <path d="M{x+20} {top+14}V{bottom-7}" stroke="#b78d71" stroke-opacity=".5" stroke-width="1.3"/>
    </g>'''


def _endurance(prefix):
    # Deterministic conceptual curves have a shared origin and no payoff floor.
    outcomes = [90, 118, 146, 176, 208, 239, 269, 298, 326, 351, 375, 397,
                420, 443, 466, 489, 511, 531]
    paths = []
    for index, end in enumerate(outcomes):
        spread = end-410
        bend = math.sin(index*.93)*22
        d = (f'M82 410 C153 407 179 {407+spread*.1:.1f} 240 {401+spread*.22:.1f} '
             f'S354 {409+spread*.41+bend:.1f} 425 {399+spread*.49:.1f} '
             f'S559 {407+spread*.73-bend*.4:.1f} 610 {401+spread*.78:.1f} '
             f'S704 {end+12:.1f} 754 {end}')
        paths.append(f'<path d="{d}" fill="none" stroke="{["#ad876a", "#c1a188", "#98775f"][index%3]}" stroke-width="{1.05 if index%3 else 1.4}" stroke-opacity="{.38 if index%2 else .56}" stroke-linecap="round"/>')
    red = 'M82 410C153 408 185 393 240 375S351 331 425 307S559 241 610 211S704 161 754 141'
    return f'''
      <ellipse cx="423" cy="464" rx="321" ry="42" fill="url(#{prefix}-ground)" opacity=".63"/>
      <path d="M82 410H758" fill="none" stroke="#b9a08b" stroke-width="1" stroke-opacity=".45" stroke-dasharray="2 7"/>
      {_gate(prefix, 230, 290, 'systematic')}
      {_gate(prefix, 420, 331, 'mean')}
      {_gate(prefix, 610, 365, 'tails')}
      <g class="objective-outcomes">{''.join(paths)}</g>
      <g data-scene-part="tails">
        <path d="M82 410C172 412 192 425 240 435S356 458 425 462S561 493 610 505S713 537 754 553" fill="none" stroke="#a4775b" stroke-opacity=".48" stroke-width="1.4"/>
        <path d="M82 410C165 410 186 383 240 352S350 283 425 223S553 155 610 112S718 71 754 57" fill="none" stroke="#aa8166" stroke-opacity=".38" stroke-width="1.4"/>
      </g>
      <g data-scene-part="mean">
        <path d="{red}" transform="translate(0 3)" fill="none" stroke="#885036" stroke-opacity=".11" stroke-width="6"/>
        <path class="scene-flow" d="{red}" fill="none" stroke="url(#{prefix}-oxblood)" stroke-width="3.4" stroke-linecap="round"/>
        <path d="M597 215C632 195 659 181 684 171" fill="none" stroke="#f4c2a4" stroke-opacity=".75" stroke-width=".8"/>
        {_bead(prefix, 754, 141, 5, True)}
      </g>
      {_gate(prefix, 230, 290, 'systematic', True)}
      {_gate(prefix, 420, 331, 'mean', True)}
      {_gate(prefix, 610, 365, 'tails', True)}
      <g data-scene-part="systematic">
        {_disc(prefix, 82, 417, 24, 10, depth=6)}
        {_bead(prefix, 82, 410, 8.5, True)}
        <path d="M109 410C140 410 160 405 181 399" fill="none" stroke="#8b0000" stroke-width="2.1" marker-end="url(#{prefix}-red-arrow)"/>
      </g>'''


def _why_now(prefix):
    loop = 'M486 184C599 196 641 296 583 378C516 473 337 480 254 385C193 315 221 218 298 187C350 165 400 164 445 175'
    return f'''
      <ellipse cx="403" cy="465" rx="316" ry="57" fill="url(#{prefix}-ground)"/>
      <g data-scene-part="dividends">
        <path d="M298 234C220 233 190 198 113 184" fill="none" stroke="#bc9b82" stroke-width="3" stroke-linecap="round"/>
        <path d="M245 222C208 214 185 200 158 195" fill="none" stroke="#a47b5e" stroke-width="1.4" marker-end="url(#{prefix}-copper-arrow)"/>
        {_disc(prefix, 109, 192, 41, 16, depth=8)}
        {_disc(prefix, 109, 180, 37, 14, depth=7)}
        {_disc(prefix, 109, 169, 32, 12, depth=6)}
        <ellipse cx="109" cy="168" rx="21" ry="6.5" fill="none" stroke="#a98267" stroke-opacity=".57"/>
      </g>
      <g data-scene-part="repurchases">
        <path d="M512 231C572 218 607 180 675 176" fill="none" stroke="#bc9b82" stroke-width="3" stroke-linecap="round"/>
        <path d="M557 216C589 204 605 189 631 184" fill="none" stroke="#a47b5e" stroke-width="1.4" marker-end="url(#{prefix}-copper-arrow)"/>
        {_disc(prefix, 676, 179, 46, 19, depth=9)}
        <path d="M647 177C650 158 686 150 703 170C713 184 686 192 668 188" fill="none" stroke="url(#{prefix}-copper)" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M675 183L664 188L674 193" fill="none" stroke="#a27458" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <g data-scene-part="debt">
        <path d="M541 359C588 386 618 430 685 452" fill="none" stroke="#bc9b82" stroke-width="3" stroke-linecap="round"/>
        <path d="M588 391C612 411 627 430 650 438" fill="none" stroke="#a47b5e" stroke-width="1.4" marker-end="url(#{prefix}-copper-arrow)"/>
        {_disc(prefix, 685, 459, 46, 19, depth=9)}
        <path d="M655 437L684 423L714 437L684 452Z" fill="url(#{prefix}-ceramic)" stroke="#fff9ed"/>
        <path d="M655 437V450L684 466V452Z" fill="#d6bca7"/>
        <path d="M684 452L714 437V450L684 466Z" fill="url(#{prefix}-edge)"/>
        <path d="M674 437L684 432L695 437L684 443Z" fill="url(#{prefix}-copper)"/>
      </g>
      <g data-scene-part="acquisitions">
        <path d="M272 360C202 375 180 427 108 453" fill="none" stroke="#bc9b82" stroke-width="3" stroke-linecap="round"/>
        <path d="M222 384C195 402 181 419 155 432" fill="none" stroke="#a47b5e" stroke-width="1.4" marker-end="url(#{prefix}-copper-arrow)"/>
        {_disc(prefix, 105, 460, 48, 19, depth=9)}
        {_disc(prefix, 91, 442, 23, 11, depth=10)}
        {_disc(prefix, 122, 442, 23, 11, depth=10)}
        <path d="M92 434Q106 426 121 434" fill="none" stroke="#98684e" stroke-width="1.8"/>
      </g>
      <g data-scene-part="reinvestment">
        <path d="{loop}" transform="translate(0 9)" fill="none" stroke="#815540" stroke-opacity=".16" stroke-width="26" stroke-linecap="round"/>
        <path d="{loop}" fill="none" stroke="#6b1620" stroke-width="20" stroke-linecap="round"/>
        <path class="scene-flow" d="{loop}" transform="translate(0 -2)" fill="none" stroke="url(#{prefix}-oxblood)" stroke-width="17" stroke-linecap="round"/>
        <path d="M489 178C596 194 631 287 578 372C509 464 341 468 260 379" fill="none" stroke="#ebad91" stroke-opacity=".56" stroke-width="1.2" stroke-linecap="round"/>
        <path d="M430 160L463 179L428 190Z" fill="url(#{prefix}-oxblood)" stroke="#b45348" stroke-width=".8" filter="url(#{prefix}-close)"/>
        <path d="M295 428L267 407L267 438Z" fill="url(#{prefix}-oxblood)" stroke="#b45348" stroke-width=".8"/>
        <path d="M404 397V355M404 238V188" fill="none" stroke="#b5866b" stroke-width="3"/>
        <path d="M403 382V363M403 223V207" fill="none" stroke="#8b0000" stroke-width="1.6" marker-end="url(#{prefix}-red-arrow)"/>
        {_disc(prefix, 400, 332, 96, 39, depth=18)}
        {_disc(prefix, 400, 310, 79, 32, depth=14)}
        <g filter="url(#{prefix}-cast)">
          <path d="M348 279L399 253L453 279V306L400 334L348 306Z" fill="url(#{prefix}-edge)" stroke="#bc9a80" stroke-width=".8"/>
          <path d="M348 279L399 253L453 279L400 306Z" fill="url(#{prefix}-ceramic)" stroke="#fffaf0"/>
          <path d="M400 306V333" fill="none" stroke="#a98468" stroke-width=".9"/>
          <path d="M364 270L400 252L436 270L400 289Z" fill="url(#{prefix}-ceramic)" stroke="#fffdf5"/>
          <path d="M364 270V282L400 302V289Z" fill="#d9c1ab"/>
          <path d="M400 289L436 270V282L400 302Z" fill="#b08b6e"/>
          <path d="M383 267L400 258L418 267L400 276Z" fill="url(#{prefix}-oxblood)" stroke="#c07861" stroke-width=".6"/>
        </g>
        {_bead(prefix, 403, 395, 5.5, True)}
        {_bead(prefix, 403, 238, 5.5, True)}
      </g>'''


def objective_scene(kind, uid):
    """Return one decorative, self-contained SVG with unique prefixed IDs.

    ``kind`` is economics, endurance, or why-now. Pass a distinct ``uid`` for
    each occurrence so gradients, markers and shadows remain local to it.
    """
    scenes = {'economics': _economics, 'endurance': _endurance, 'why-now': _why_now}
    if kind not in scenes:
        raise ValueError(f'Unknown objective scene: {kind}')
    prefix = re.sub(r'[^A-Za-z0-9_-]+', '-', str(uid)).strip('-') or 'objective'
    artwork = scenes[kind](prefix).replace('class="scene-flow"', 'class="scene-flow" pathLength="1"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="objective-sculpture" '
            f'viewBox="0 0 800 600" aria-hidden="true" focusable="false" '
            f'data-objective-scene="{kind}">{_defs(prefix)}{artwork}</svg>')
