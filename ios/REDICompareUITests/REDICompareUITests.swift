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
}
