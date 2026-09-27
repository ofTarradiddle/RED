# Launch REDI Play

The website game can publish independently. Native TestFlight and App Store
distribution remain blocked by Apple Developer Program enrollment and signing.
The current repository has no Apple account, team, signing certificate or App
Store Connect app record configured.

## The publisher's next step

[Enroll with Apple](https://developer.apple.com/programs/enroll/). Apple lists
membership at US$99 per year, with regional pricing. Individual enrollment shows
the person's legal name as seller. Organization enrollment shows the legal
entity name and requires Apple's organization verification, including a D-U-N-S
number where applicable. Choose the actual legal publisher; a trade name alone
is not an enrolled organization. Do not share the Apple password in chat.

## After enrollment

1. Add the Apple account in Xcode → Settings → Accounts. Select the enrolled
   signing team for the REDICompare target (display name REDI Play). Confirm the
   proposed `com.hetzerk.REDIPlay` identifier is available for that team. Keep
   personal signing settings out of Git.
2. Create the REDI Play record in App Store Connect with the same identifier.
   Review `metadata.md`, publisher identity, privacy answers, age rating and
   rights to the historical data. Use the real native review screenshots.
3. Build the Release archive in full Xcode. The automated unsigned archive proves
   the app builds; it is not an installable App Store package. Use Organizer →
   Distribute App → App Store Connect with the enrolled team.
4. After processing, enable TestFlight for initial device testing. Confirm offline
   play, persistence, long-number layout, reduced motion, comparison refresh and
   sources on physical phones. External beta distribution may require review.
5. Select the reviewed build, finish the store record and submit to App Review.
   An upload or successful compilation does not guarantee approval. Release the
   app after Apple approves it and the publisher chooses availability.

Official references: [enrollment](https://developer.apple.com/programs/enroll/),
[uploading builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/),
[TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/),
[review](https://developer.apple.com/app-store/review/).
