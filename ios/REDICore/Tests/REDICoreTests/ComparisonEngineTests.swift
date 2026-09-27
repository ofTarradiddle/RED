import Foundation
import XCTest
@testable import REDICore

final class ComparisonEngineTests: XCTestCase {
    private func row(_ date: String, _ price: Double, nav: Double? = nil,
                     dividend: Double = 0, split: Double? = nil, adjusted: Double? = nil) -> Observation {
        Observation(date: date, marketPrice: price, nav: nav, distribution: dividend,
                    split: split, adjustedClose: adjusted)
    }

    private func fund(_ id: String, _ rows: [Observation], illustrative: Bool = false) -> FundSeries {
        FundSeries(id: id, name: id + " ETF", source: "Test closing data",
                   isIllustrative: illustrative, observations: rows)
    }

    private func snapshot(_ funds: [FundSeries]) -> MarketSnapshot {
        MarketSnapshot(generatedAt: "2026-09-26T22:57:03.814343+00:00", expenseRatio: 0.0045, series: funds)
    }

    private func compare(_ funds: [FundSeries], basis: REDIBasis = .marketPrice,
                         mode: ReturnMode = .price, period: ComparisonPeriod = .all) throws -> REDICore.ComparisonResult {
        try ComparisonEngine.compare(snapshot: snapshot(funds), settings: ComparisonSettings(
            peers: funds.filter { $0.id != "REDI" }.map(\.id), basis: basis, returnMode: mode, period: period))
    }

    private func sessions(count: Int = 25) -> [String] {
        let start = TradingDate.parse("2026-01-02")!
        var days: [String] = []
        var offset = 0
        while days.count < count {
            let date = TradingDate.calendar.date(byAdding: .day, value: offset, to: start)!
            let weekday = TradingDate.calendar.component(.weekday, from: date)
            if weekday != 1 && weekday != 7 { days.append(TradingDate.string(date)) }
            offset += 1
        }
        return days
    }

    func testDistributionIsReinvestedExactlyOnceAndAdjustedCloseIsNotUsed() throws {
        let redi = fund("REDI", [row("2026-01-02", 100, adjusted: 70),
                                 row("2026-01-05", 98, dividend: 2, adjusted: 120),
                                 row("2026-01-06", 107.8, adjusted: 160)])
        let reinvested = try compare([redi], mode: .reinvested)
        XCTAssertEqual(try XCTUnwrap(reinvested.series.first?.metrics.change), 0.1, accuracy: 1e-12)
        XCTAssertEqual(try XCTUnwrap(reinvested.series.first?.points[1].value), 100, accuracy: 1e-12)
        XCTAssertEqual(try XCTUnwrap(compare([redi]).series.first?.metrics.change), 0.078, accuracy: 1e-12)
    }

    func testUnmatchedExDateStillContributesToReinvestedWealth() throws {
        let redi = fund("REDI", [row("2026-01-02", 100), row("2026-01-05", 98, dividend: 2), row("2026-01-06", 100)])
        let spy = fund("SPY", [row("2026-01-02", 50), row("2026-01-06", 51)])
        let result = try compare([redi, spy], mode: .reinvested)
        XCTAssertEqual(result.dates, ["2026-01-02", "2026-01-06"])
        XCTAssertEqual(try XCTUnwrap(result.series.first?.metrics.change), 100.0 / 98 - 1, accuracy: 1e-12)
    }

    func testSplitAdjustedPriceDoesNotReceiveAnotherSplitAdjustment() throws {
        let redi = fund("REDI", [row("2026-01-02", 50), row("2026-01-05", 51, split: 2)])
        XCTAssertEqual(try XCTUnwrap(compare([redi], mode: .reinvested).series.first?.metrics.change), 0.02, accuracy: 1e-12)
    }

    func testNAVSelectionOnlyChangesREDIAndHonorsCommonHorizon() throws {
        let redi = fund("REDI", [row("2026-01-02", 90, nav: 100), row("2026-01-05", 100, nav: 105),
                                 row("2026-01-06", 120, nav: 110)], illustrative: true)
        let spy = fund("SPY", [row("2026-01-05", 200, nav: 400), row("2026-01-06", 202, nav: 600)])
        let result = try compare([redi, spy], basis: .nav)
        XCTAssertEqual(result.start, "2026-01-05")
        XCTAssertEqual(result.end, "2026-01-06")
        XCTAssertEqual(result.series.map { $0.points.first!.value }, [100, 100])
        XCTAssertTrue(result.series[0].isIllustrative)
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.change), 110.0 / 105 - 1, accuracy: 1e-12)
        XCTAssertEqual(try XCTUnwrap(result.series[1].metrics.change), 0.01, accuracy: 1e-12)
    }

    func testYTDUsesPriorYearSharedClosingValue() throws {
        let redi = fund("REDI", [row("2025-12-30", 80), row("2025-12-31", 100), row("2026-01-02", 110)])
        let result = try compare([redi], period: .yearToDate)
        XCTAssertEqual(result.start, "2025-12-31")
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.change), 0.1, accuracy: 1e-12)
    }

    func testCalendarMonthCutoffsClampEndOfMonthAndLeapYear() {
        XCTAssertEqual(TradingDate.cutoff(end: "2026-03-31", period: .oneMonth), "2026-02-28")
        XCTAssertEqual(TradingDate.cutoff(end: "2024-03-31", period: .oneMonth), "2024-02-29")
        XCTAssertEqual(TradingDate.cutoff(end: "2024-02-29", period: .oneYear), "2023-02-28")
        XCTAssertNil(TradingDate.cutoff(end: "2026-03-31", period: .all))
    }

    func testDrawdownIsMeasuredFromRunningPeak() throws {
        let redi = fund("REDI", [row("2026-01-02", 100), row("2026-01-05", 125),
                                 row("2026-01-06", 100), row("2026-01-07", 115)])
        let result = try compare([redi])
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.drawdown), -0.2, accuracy: 1e-12)
    }

    func testRiskNeedsTwentyMatchedDailyReturns() throws {
        let rows = sessions(count: 21).enumerated().map { index, date in row(date, 100 + Double(index % 3)) }
        let short = try compare([fund("REDI", Array(rows.prefix(20)))])
        XCTAssertNil(short.series[0].metrics.volatility)
        XCTAssertNotNil(short.riskReason)
        let sufficient = try compare([fund("REDI", rows)])
        XCTAssertNotNil(sufficient.series[0].metrics.volatility)
        XCTAssertEqual(try XCTUnwrap(sufficient.series[0].metrics.correlation), 1, accuracy: 1e-12)
        XCTAssertNil(sufficient.riskReason)
    }

    func testVolatilityUsesSampleVarianceAnd252Sessions() throws {
        let dates = sessions(count: 21)
        var price = 100.0
        var rows = [row(dates[0], price)]
        let daily = (0..<20).map { $0 % 2 == 0 ? 0.01 : -0.01 }
        for (index, value) in daily.enumerated() { price *= 1 + value; rows.append(row(dates[index + 1], price)) }
        let result = try compare([fund("REDI", rows)])
        let expected = sqrt((20 * 0.0001 / 19) * 252)
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.volatility), expected, accuracy: 1e-12)
    }

    func testCorrelationWithConstantSeriesIsUnavailableNotZero() throws {
        let dates = sessions()
        let redi = fund("REDI", dates.map { row($0, 100) })
        let spy = fund("SPY", dates.enumerated().map { row($1, 100 + Double($0 % 3)) })
        let result = try compare([redi, spy])
        XCTAssertEqual(result.series[0].metrics.volatility, 0)
        XCTAssertNil(result.series[0].metrics.correlation)
        XCTAssertNil(result.series[1].metrics.correlation)
    }

    func testMissingPeerSessionWithholdsRiskWithoutForwardFilling() throws {
        let rows = sessions(count: 26).enumerated().map { row($1, 100 + Double($0 % 3)) }
        let redi = fund("REDI", rows)
        let spy = fund("SPY", rows)
        let itan = fund("ITAN", rows.enumerated().filter { $0.offset != 5 }.map(\.element))
        let result = try compare([redi, spy, itan])
        XCTAssertEqual(result.dates.count, 25)
        XCTAssertFalse(result.dates.contains(rows[5].date))
        XCTAssertNil(result.series[0].metrics.volatility)
        XCTAssertTrue(result.riskReason?.contains("gaps") == true)
    }

    func testExtraWorkbookHolidayDoesNotInvalidatePeerCalendar() throws {
        let rows = sessions().enumerated().map { row($1, 100 + Double($0 % 3)) }
        let redi = fund("REDI", rows + [row("2026-01-03", 100)])
        let result = try compare([redi, fund("SPY", rows)])
        XCTAssertEqual(result.dates.count, 25)
        XCTAssertNotNil(result.series[0].metrics.volatility)
    }

    func testLongSharedGapWithholdsDailyRisk() throws {
        let rows = sessions(count: 33).enumerated().filter { !(5...10).contains($0.offset) }
            .map { row($1, 100 + Double($0 % 3)) }
        let result = try compare([fund("REDI", rows), fund("SPY", rows)])
        XCTAssertGreaterThan(result.dates.count, 21)
        XCTAssertNil(result.series[0].metrics.volatility)
        XCTAssertTrue(result.riskReason?.contains("gaps") == true)
    }

    func testMissingNAVOnDistributionExDateBlocksReinvestedComparison() throws {
        let redi = fund("REDI", [row("2026-01-02", 100, nav: 100), row("2026-01-05", 98, dividend: 2),
                                 row("2026-01-06", 100, nav: 100)])
        let result = try compare([redi], basis: .nav, mode: .reinvested)
        XCTAssertTrue(result.series.isEmpty)
        XCTAssertTrue(result.warnings.contains { $0.contains("ex-date") })
        XCTAssertEqual(try compare([redi], basis: .nav).dates.count, 2)
    }

    func testUnavailableFundIsExplicitlyExcluded() throws {
        let redi = fund("REDI", [row("2026-01-02", 100), row("2026-01-05", 101)])
        let result = try compare([redi, fund("SPY", [])])
        XCTAssertEqual(result.series.map(\.id), ["REDI"])
        XCTAssertTrue(result.warnings.contains { $0.hasPrefix("SPY:") })
    }

    func testNoCommonDateAndSingleDateDoNotInventPerformance() throws {
        let single = try compare([fund("REDI", [row("2026-01-02", 100)])])
        XCTAssertNil(single.series[0].metrics.change)
        XCTAssertNil(single.series[0].metrics.drawdown)
        let mismatch = try compare([fund("REDI", [row("2026-01-02", 100)]),
                                    fund("SPY", [row("2026-01-05", 100)])])
        XCTAssertTrue(mismatch.series.isEmpty)
        XCTAssertNil(mismatch.start)
    }

    func testValidationRejectsAllInvalidObservationsEvenWhenUnselected() throws {
        let good = fund("REDI", [row("2026-01-02", 100)])
        let invalid = [row("2026-02-30", 100), row("2026-1-02", 100), row("2026-01-02", 0),
                       row("2026-01-02", -.infinity), row("2026-01-02", 100, nav: -1),
                       row("2026-01-02", 100, dividend: -1), row("2026-01-02", 100, dividend: .nan),
                       row("2026-01-02", 100, split: -1), row("2026-01-02", 100, adjusted: .infinity)]
        for bad in invalid {
            XCTAssertThrowsError(try ComparisonEngine.compare(snapshot: snapshot([good, fund("SPY", [bad])]),
                                                               settings: ComparisonSettings(peers: [])))
        }
        XCTAssertThrowsError(try snapshot([fund("REDI", [row("2026-01-02", 100), row("2026-01-02", 101)])]).validated())
        XCTAssertThrowsError(try snapshot([good, good]).validated())
        XCTAssertThrowsError(try snapshot([good, fund("UNKNOWN", [])]).validated())
        XCTAssertThrowsError(try snapshot([fund("SPY", [])]).validated())
        XCTAssertThrowsError(try MarketSnapshot(schemaVersion: 2, generatedAt: "", expenseRatio: 0.0045, series: [good]).validated())
        XCTAssertThrowsError(try MarketSnapshot(generatedAt: "", expenseRatio: .nan, series: [good]).validated())
        XCTAssertThrowsError(try snapshot([FundSeries(id: "REDI", name: "REDI", currency: "EUR", source: "Test", observations: [])]).validated())
    }

    func testCanonicalDatesAllowLeapDayButRejectNormalization() {
        XCTAssertTrue(TradingDate.isValid("2024-02-29"))
        for date in ["2026-02-29", "2026-13-01", "2026-01-00", "2026-01-2", "2026-01-02T00:00:00Z", "0000-01-01"] {
            XCTAssertFalse(TradingDate.isValid(date), date)
        }
    }

    func testSettingsRejectUnknownAndRepeatedPeers() {
        let data = snapshot([fund("REDI", [])])
        for peers in [["REDI"], ["SPY", "SPY"], ["UNSUPPORTED"]] {
            XCTAssertThrowsError(try ComparisonEngine.compare(snapshot: data, settings: ComparisonSettings(peers: peers)))
        }
    }

    func testExplicitWireKeysDecodeAndRoundTripWithoutKeyConversion() throws {
        let json = """
        {"schema_version":1,"generated_at":"2026-09-26T22:57:03.814343+00:00",
         "market_refresh_at":"2026-09-26T22:50:11Z","last_attempt_at":null,"status":"ok","expense_ratio":0.0045,
         "series":[{"id":"REDI","name":"Hetzerk Innovation Factor ETF","currency":"USD","kind":"etf",
         "source":"Illustrative workbook","source_url":"/review/","as_of":"2026-09-18","status":"ok",
         "is_illustrative":true,"observations":[{"date":"2026-09-18","market_price":25,"nav":24.9,
         "distribution":0,"split":0,"adjusted_close":24}]}]}
        """
        let data = Data(json.utf8)
        let value = try JSONDecoder().decode(MarketSnapshot.self, from: data).validated()
        XCTAssertEqual(value.expenseRatio, 0.0045)
        XCTAssertEqual(value.series[0].sourceURL, "/review/")
        XCTAssertTrue(value.series[0].isIllustrative)
        XCTAssertEqual(value.series[0].observations[0].marketPrice, 25)
        XCTAssertEqual(value.series[0].observations[0].adjustedClose, 24)
        let roundTrip = try JSONDecoder().decode(MarketSnapshot.self, from: JSONEncoder().encode(value)).validated()
        XCTAssertEqual(roundTrip.series[0].observations[0].nav, 24.9)
        for broken in [json.replacingOccurrences(of: "\"distribution\":0,", with: ""),
                       json.replacingOccurrences(of: "\"market_price\":25", with: "\"market_price\":null"),
                       json.replacingOccurrences(of: "\"is_illustrative\":true", with: "\"is_illustrative\":\"true\""),
                       json.replacingOccurrences(of: "\"market_price\":25", with: "\"market_price\":\"25\"")] {
            XCTAssertThrowsError(try JSONDecoder().decode(MarketSnapshot.self, from: Data(broken.utf8)))
        }
    }

    func testSavedSettingsRoundTrip() throws {
        let value = ComparisonSettings(peers: ["VOO", "QQQ"], basis: .nav, returnMode: .reinvested, period: .yearToDate)
        XCTAssertEqual(try JSONDecoder().decode(ComparisonSettings.self, from: JSONEncoder().encode(value)), value)
    }
}
