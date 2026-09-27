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
}
