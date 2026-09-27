# REDI Play — App Store Connect draft

Status: native review build. The publisher has not enrolled in the Apple
Developer Program. No TestFlight build or App Store listing is live.

**Name:** REDI Play

**Subtitle:** Invest through innovation

**Primary category:** Games (Simulation / Strategy, subject to the publisher's final category selection)

**Secondary category:** Finance

**Proposed bundle identifier:** `com.hetzerk.REDIPlay`

**Description:**

Start with $100. Build a portfolio. Let the years answer.

REDI Play begins at year-end 2010. Explore a reconstruction of that year's S&P 500
constituents, inspect company filings available at the time, and choose portfolio
weights across supported firms. Invest up to 100% in total; leave the rest in cash.
Then advance a year and inspect the resulting portfolio and individual firm returns.
Prepare an equal-weight draft across the supported universe, then edit it before
locking. Inspect completed company returns against SPY and track linked returns
through only the periods you held each firm, alongside your dollar profit.

Follow your actual invested periods across repeated entries and exits. Compare
the portfolio's observed path with an ETF market proxy, resume offline, and keep
replay-verified device scores. The smaller Classic and Daily arcade is also available
as a separate exercise, with its own progress and scores.

Explore native ETF comparison tools alongside the game: dated market-price
history, NAV where available, drawdown, volatility and correlation. Save a
comparison and inspect the source and calculation assumptions.

Open the strategy research archive from Compare or REDI. Explore monthly
Innovation Leader, Laggard and Market Backtest levels with logarithmic or linear
charts, inspect individual months, and overlay available ETF histories over a
shared period. The source archive is bundled for offline use. These hypothetical
research levels are transcribed and rounded; source fee and dividend assumptions
are unspecified, and the underlying backtest has not been independently verified.
They are separate from REDI NAV and actual fund performance.

The annual universe is a public historical reconstruction, not an official licensed
index record. Every constituent remains visible, but incomplete, delisted or
ambiguous return paths cannot be used until supported. This creates coverage bias.
The game uses provider-adjusted returns and dated financial evidence; it is an
educational exercise, not a test that predicts investing ability. All game money
is fictional. There are no brokerage
connections, real-money wagers, prizes or in-app purchases. Past performance does
not predict future results.

**Review notes:**

- No login is required. Tap Play → Build Your Portfolio. Search a historical
  company, inspect its record, enter a portfolio percentage, and Apply Weight.
  Combined weights must stay at or below 100%. Lock the Portfolio advances one
  annual period; an empty allocation holds cash. The final partial year ends at
  the source's latest completed observation. Tap the trophy for local scores.
- Equal weight universe fills an editable draft using the full supported roster,
  not just search results. It never submits an allocation automatically. Revealed
  universe rows open completed company/SPY return paths even for unheld firms.
- Game content and JavaScriptCore rules are bundled and work offline; the native
  UI is SwiftUI, not a website wrapper. No executable code is downloaded.
- Each annual rebalance closes previous return-unit lots at observed marks and
  reallocates current capital. Provider dividend and split adjustments are not
  credited twice. Cash earns 0%; fees, taxes and inflation are excluded.
- The information button documents rules, coverage limitations and privacy.
  Individual company records link dated original filings and distinguish missing
  financials from zero. The secondary arcade respects Reduce Motion and offers
  optional haptic feedback.
- The Compare, Risk and REDI tabs use a dated public website feed. REDI remains
  marked as illustrative until its verified live feed is supplied.
- Tap “The measure of fire” in Compare or REDI for offline strategy research.
  It does not require a market refresh. Research methods and source limitations
  are in the sheet; optional ETF overlays use the cached comparison feed.
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
Annual portfolio home, dated company evidence, annual results and owned-period
history, plus the secondary arcade, comparison tools and research.
Do not label simulator screenshots as an App Store release or promote fictional
capital as a real investment outcome.

**Enrollment and release:** See [launch steps](LAUNCH.md).
