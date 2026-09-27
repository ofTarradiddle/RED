import XCTest

final class REDICompareUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        XCTAssertTrue(app.buttons["peer-SPY"].waitForExistence(timeout: 15))
    }

    private func screenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func reveal(_ element: XCUIElement, scrollingUp: Bool = true) {
        for _ in 0..<5 where !element.isHittable {
            if scrollingUp { app.swipeUp() } else { app.swipeDown() }
        }
        XCTAssertTrue(element.isHittable)
    }

    func testNativeComparisonAndPeerLimit() {
        screenshot("01-compare")
        app.buttons["peer-VOO"].tap()
        XCTAssertFalse(app.buttons["peer-QQQ"].isEnabled)
        app.buttons["peer-SPY"].tap()
        XCTAssertTrue(app.buttons["peer-QQQ"].isEnabled)
        app.buttons["peer-QQQ"].tap()
        app.swipeUp()
        XCTAssertTrue(app.descendants(matching: .any)["compare-chart"].firstMatch.waitForExistence(timeout: 8))
        screenshot("02-native-chart")
    }

    func testNativeRiskAndFundTabs() {
        app.tabBars.buttons["Risk"].tap()
        XCTAssertTrue(app.staticTexts["Beyond the\nending value."].waitForExistence(timeout: 8))
        screenshot("03-risk")
        app.tabBars.buttons["REDI"].tap()
        XCTAssertTrue(app.staticTexts["REDI for\ntomorrow."].waitForExistence(timeout: 8))
        screenshot("04-fund")
    }

    func testBookmarkSheetAndDevelopmentDismissal() {
        let close = app.buttons["development-close"]
        if close.exists { close.tap(); XCTAssertFalse(close.exists) }
        app.buttons["saved-button"].tap()
        XCTAssertTrue(app.navigationBars["Saved comparisons"].waitForExistence(timeout: 8))
        let name = app.textFields["saved-name"]
        name.tap()
        name.typeText("My market view")
        app.buttons["save-comparison-button"].tap()
        XCTAssertTrue(app.staticTexts["My market view"].waitForExistence(timeout: 8))
        screenshot("05-saved-comparisons")
        app.staticTexts["My market view"].tap()
        XCTAssertTrue(app.buttons["peer-SPY"].waitForExistence(timeout: 8))
    }

    func testNativePlayRoundAndResume() {
        app.tabBars.buttons["Play"].tap()
        reveal(app.buttons["annual-quick"])
        app.buttons["annual-quick"].tap()
        XCTAssertTrue(app.buttons["play-classic"].waitForExistence(timeout: 15))
        screenshot("06-play-home")
        app.buttons["play-classic"].tap()
        XCTAssertTrue(app.buttons["play-choice-25"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["play-round"].label, "1 / 12")
        screenshot("07-play-decision")
        app.buttons["play-choice-25"].tap()
        XCTAssertTrue(app.buttons["play-next"].waitForExistence(timeout: 10))
        screenshot("08-play-reveal")
        app.buttons["play-home"].tap()
        XCTAssertTrue(app.buttons["play-resume"].waitForExistence(timeout: 8))
        app.buttons["play-resume"].tap()
        XCTAssertTrue(app.buttons["play-next"].waitForExistence(timeout: 8))
        app.buttons["play-next"].tap()
        XCTAssertEqual(app.staticTexts["play-round"].label, "2 / 12")
    }

    func testNativeDailyRunFinishesAndVerifiesDeviceScore() {
        app.tabBars.buttons["Play"].tap()
        reveal(app.buttons["annual-quick"])
        app.buttons["annual-quick"].tap()
        XCTAssertTrue(app.buttons["play-daily"].waitForExistence(timeout: 15))
        app.buttons["play-daily"].tap()
        for _ in 0..<12 {
            XCTAssertTrue(app.buttons["play-choice-0"].waitForExistence(timeout: 10))
            app.buttons["play-choice-0"].tap()
            XCTAssertTrue(app.buttons["play-next"].waitForExistence(timeout: 10))
            app.buttons["play-next"].tap()
        }
        XCTAssertTrue(app.buttons["play-again"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["play-finish-capital"].label, "$100.00")
        screenshot("09-play-finish")
        app.buttons["play-scores"].tap()
        XCTAssertTrue(app.navigationBars["Device leaderboard"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["$100.00"].exists)
        screenshot("10-play-scores")
    }

    func testResearchArchiveSelectionPeriodScaleAndFundEntry() {
        reveal(app.buttons["research-open-compare"], scrollingUp: false)
        app.buttons["research-open-compare"].tap()
        XCTAssertTrue(app.navigationBars["Strategy research"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["research-disclaimer"].exists)
        XCTAssertEqual(app.buttons["research-series-INNOVATION_LEADER"].value as? String, "Selected")
        XCTAssertFalse(app.buttons["research-series-INNOVATION_LEADER"].isEnabled)
        app.buttons["research-series-LAGGARD"].tap()
        XCTAssertEqual(app.buttons["research-series-LAGGARD"].value as? String, "Not selected")
        reveal(app.segmentedControls["research-period"])
        app.segmentedControls["research-period"].buttons["5Y"].tap()
        let chart = app.descendants(matching: .any)["research-chart"].firstMatch
        XCTAssertTrue(chart.waitForExistence(timeout: 8))
        reveal(chart)
        XCTAssertEqual(app.staticTexts["research-window"].label, "2021-08-31 — 2026-08-31")
        XCTAssertEqual(app.staticTexts["research-chart-title"].label, "Log returns")
        let middle = chart.coordinate(withNormalizedOffset: CGVector(dx: 0.50, dy: 0.50))
        middle.press(forDuration: 0.1, thenDragTo: chart.coordinate(withNormalizedOffset: CGVector(dx: 0.60, dy: 0.50)))
        let inspector = app.staticTexts["research-inspected-date"]
        let inspectedMonth = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label BEGINSWITH %@ AND label != %@", "Month end · ", "Month end · 2026-08-31"),
            object: inspector)
        let inspectionState = XCTWaiter.wait(for: [inspectedMonth], timeout: 3)
        screenshot("11-research-log")
        XCTAssertEqual(inspectionState, .completed)
        let retainedMonth = inspector.label
        XCTAssertNotEqual(retainedMonth, "Month end · 2026-08-31")
        reveal(app.segmentedControls["research-scale"], scrollingUp: false)
        app.segmentedControls["research-scale"].buttons["Linear"].tap()
        XCTAssertEqual(inspector.label, retainedMonth)
        reveal(app.buttons["research-series-SPY"], scrollingUp: false)
        app.buttons["research-series-SPY"].tap()
        reveal(chart)
        XCTAssertEqual(app.staticTexts["research-chart-title"].label, "Growth of $100")
        XCTAssertTrue(app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH 'ETF session · '")).firstMatch.exists)
        screenshot("12-research-etf-overlay")
        app.buttons["research-done"].tap()
        XCTAssertTrue(app.buttons["peer-SPY"].waitForExistence(timeout: 8))
        app.tabBars.buttons["REDI"].tap()
        reveal(app.buttons["research-open-fund"])
        app.buttons["research-open-fund"].tap()
        XCTAssertTrue(app.navigationBars["Strategy research"].waitForExistence(timeout: 8))
    }

    func testAnnualPortfolioAllocationOwnedPeriodsAndResume() {
        app.tabBars.buttons["Play"].tap()
        XCTAssertTrue(app.buttons["annual-start"].waitForExistence(timeout: 20))
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true"), object: app.buttons["annual-start"])
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 45), .completed)
        screenshot("13-annual-portfolio-home")
        app.buttons["annual-start"].tap()
        XCTAssertTrue(app.textFields["annual-search"].waitForExistence(timeout: 15))
        XCTAssertEqual(app.staticTexts["annual-round"].label, "1 / 16")
        let search = app.textFields["annual-search"]
        reveal(search)
        search.tap(); search.typeText("AAPL\n")
        reveal(app.buttons["annual-equal-universe"], scrollingUp: false)
        app.buttons["annual-equal-universe"].tap()
        reveal(app.staticTexts["annual-selected-count"])
        let selectedCount = Int(app.staticTexts["annual-selected-count"].label.split(separator: " ").first ?? "0") ?? 0
        XCTAssertGreaterThan(selectedCount, 100, "The universe action must include supported companies beyond the AAPL search filter.")
        XCTAssertTrue(app.staticTexts["annual-weight-total"].label.contains("100"))
        reveal(app.staticTexts["annual-round"], scrollingUp: false)
        XCTAssertEqual(app.staticTexts["annual-round"].label, "1 / 16")
        XCTAssertFalse(app.staticTexts["annual-result-capital"].exists, "Equal weighting prepares an editable draft without committing the year.")
        screenshot("14-annual-equal-weight-draft")
        app.buttons["annual-clear"].tap()
        reveal(app.staticTexts["annual-selected-count"])
        XCTAssertEqual(app.staticTexts["annual-selected-count"].label, "0 selected")
        reveal(search, scrollingUp: false)
        search.tap(); search.typeText("AAPL\n")
        XCTAssertTrue(app.buttons["annual-open-AAPL"].waitForExistence(timeout: 8))
        app.buttons["annual-open-AAPL"].tap()
        XCTAssertTrue(app.textFields["annual-weight-input"].waitForExistence(timeout: 8))
        screenshot("14-annual-filed-evidence")
        app.buttons["25"].tap()
        app.buttons["annual-weight-apply"].tap()
        XCTAssertTrue(app.staticTexts["annual-weight-total"].label.contains("25"))
        app.buttons["annual-commit"].tap()
        XCTAssertTrue(app.staticTexts["annual-result-capital"].waitForExistence(timeout: 15))
        screenshot("15-annual-portfolio-return")
        reveal(app.buttons["annual-history-AAPL"])
        app.buttons["annual-history-AAPL"].tap()
        let ownedSheetOpened = app.navigationBars["Your invested periods"].waitForExistence(timeout: 8)
        screenshot("16-annual-owned-sheet-open")
        XCTAssertTrue(ownedSheetOpened)
        XCTAssertEqual(app.staticTexts["annual-company-period"].label, "2011-01-03 → 2012-01-03")
        reveal(app.descendants(matching: .any)["annual-company-return-chart"].firstMatch)
        reveal(app.staticTexts["annual-owned-linked-return"])
        screenshot("16-annual-owned-periods")
        app.buttons["annual-sheet-done"].tap()
        reveal(app.segmentedControls["annual-outcomes-picker"], scrollingUp: false)
        app.segmentedControls["annual-outcomes-picker"].buttons["The year’s universe"].tap()
        let outcomeSearch = app.textFields["annual-outcome-search"]
        reveal(outcomeSearch)
        outcomeSearch.tap(); outcomeSearch.typeText("MSFT\n")
        reveal(app.buttons["annual-outcome-MSFT"])
        app.buttons["annual-outcome-MSFT"].tap()
        XCTAssertTrue(app.navigationBars["Company return record"].waitForExistence(timeout: 8))
        XCTAssertEqual(app.staticTexts["annual-company-period"].label, "2011-01-03 → 2012-01-03")
        reveal(app.staticTexts["annual-never-owned"])
        XCTAssertFalse(app.staticTexts["annual-owned-linked-return"].exists)
        screenshot("17-annual-unheld-company-return")
        app.buttons["annual-sheet-done"].tap()
        app.buttons["annual-home"].tap()
        reveal(app.buttons["annual-resume"])
        app.buttons["annual-resume"].tap()
        XCTAssertTrue(app.buttons["annual-next"].waitForExistence(timeout: 8))
        reveal(app.buttons["annual-next"])
        app.buttons["annual-next"].tap()
        XCTAssertEqual(app.staticTexts["annual-round"].label, "2 / 16")
        XCTAssertTrue(app.staticTexts["annual-cutoff"].label.contains("2011-12-31"))
    }
}
