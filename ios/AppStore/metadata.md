# REDI Play — App Store Connect draft

Status: native review build. The publisher has not enrolled in the Apple
Developer Program. No TestFlight build or App Store listing is live.

**Name:** REDI Play

**Subtitle:** Invest through innovation

**Primary category:** Games (Simulation / Strategy, subject to the publisher's final category selection)

**Secondary category:** Finance

**Proposed bundle identifier:** `com.hetzerk.REDIPlay`

**Description:**

Start with $100. Meet twelve moments that changed the world. Make the call.

REDI Play turns innovation history into a short investing game. Read the company
opportunity, inspect dated financial evidence when available, and choose how much
of your fictional capital to invest. Watch the years unfold, then decide again.

Play the same Classic route to refine your decisions, or try a new Daily route.
Resume a run offline, track your personal bests, and share your result. The
Hetzerk wing H follows your capital through six decades of business history.

Explore native ETF comparison tools alongside the game: dated market-price
history, NAV where available, drawdown, volatility and correlation. Save a
comparison and inspect the source and calculation assumptions.

The game uses selected historical companies and provider-adjusted returns. It is
an educational exercise with hindsight and survivorship bias, not a test that
predicts investing ability. All game money is fictional. There are no brokerage
connections, real-money wagers, prizes or in-app purchases. Past performance does
not predict future results.

**Review notes:**

- No login is required. Tap Play → Play Classic to start; choose Pass, 25%, 50%
  or All in, then Next Opportunity. After twelve decisions, the run is saved to
  the device board. Tap the trophy to inspect it. There is no public leaderboard.
- Game content and JavaScriptCore rules are bundled and work offline; the native
  UI is SwiftUI, not a website wrapper. No executable code is downloaded.
- Every choice closes the previous position at an observed price and reallocates
  current capital. Cash earns 0%; fees, taxes and inflation are excluded.
- The information button documents rules, source limitations and privacy. Motion
  controls and system Reduce Motion are respected. Haptic feedback is optional.
- The Compare, Risk and REDI tabs use a dated public website feed. REDI remains
  marked as illustrative until its verified live feed is supplied.
- The yellow development notice is intentional in this review build. Review
  final production wording and market-data redistribution rights before public
  submission; this draft is not a representation of App Review approval.

**Privacy URL:** `https://oftarradiddle.github.io/RED/privacy/`

**Support URL:** `https://oftarradiddle.github.io/RED/play/support.html`

Confirm the enrolled legal publisher and support contact before submitting.
Complete the current age-rating questionnaire from the actual app content;
fictional investing is not a claim of real-money gambling or a cash prize.

**Privacy implementation:** No analytics, ads, account, tracking identifier or
public upload of game scores. Canonical decisions, device scores, motion
preferences, bookmarks and cached comparison data remain on the device. The data
host receives ordinary HTTPS request metadata for comparison refreshes. Native
sharing uses the user's chosen share destination. The privacy manifest declares
the UserDefaults required-reason API. Final App Store privacy answers must
reflect the configured data host as well as the app.

**Screenshots:** Use the actual iPhone captures exported by the native CI tests:
Play home, decision, reveal, completed run, device board and comparison tools.
Do not label simulator screenshots as an App Store release or promote fictional
capital as a real investment outcome.

**Enrollment and release:** See [launch steps](LAUNCH.md).
