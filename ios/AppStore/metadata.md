# App Store Connect draft

Status: preparation only; no App Store listing or TestFlight build is published.

**Name:** REDI Compare

**Subtitle:** An ETF perspective by Hetzerk

**Category:** Finance

**Description:**

Put the Hetzerk Innovation Factor ETF beside other equity ETFs and explore how
their paths differ. Compare market prices on a shared timeline, inspect REDI's
NAV where available, and choose price change or distribution reinvestment.

Explore drawdown, volatility, and correlation with clear source dates and
methodology. Save a comparison on your device and share a dated summary through
the iOS share sheet. Your last downloaded snapshot remains available offline.

Market observations are published daily, not in real time. Fund performance,
sources, and limitations are identified in the app. Investing involves risk,
including possible loss of principal. Past performance does not predict future
results. This app does not provide investment advice or execute trades.

**Development review note:** REDI currently uses clearly marked illustrative
history; peer data is sourced from Yahoo through a public daily snapshot. There
is no account or paywall. This development build is intended for TestFlight
review. Publish the live product only after authorized market-data distribution
and the production fund feed are in place.

**Privacy/support:** Use publisher-controlled, public privacy and support URLs
in App Store Connect. The current website privacy URL is
`https://oftarradiddle.github.io/RED/privacy/`; review it for the native app before
submission. Confirm the actual support contact and legal publisher in the
Apple account rather than assuming the trade name is the enrolled entity.

**Privacy implementation:** No app analytics, advertising identifiers, account,
or tracking. Settings, bookmarks, and cached prices are stored on the device.
HTTPS requests to the public data host expose normal network information to
that host. External source links and user-selected share destinations have
their own privacy practices. `PrivacyInfo.xcprivacy` declares the UserDefaults
required-reason API; App Store Connect's privacy answers need final review by
the publisher and must reflect the data host's practices as well.

**Screenshots:** Use actual iPhone simulator captures from the native CI review
artifact. Capture final release screens after the production feed and wording
are approved; do not market illustrative REDI results as actual performance.
