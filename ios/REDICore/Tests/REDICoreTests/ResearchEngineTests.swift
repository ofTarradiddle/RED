import Foundation
import XCTest
@testable import REDICore

final class ResearchEngineTests: XCTestCase {
    private func source(_ dates: [String], _ levels: [Double], laggard: [Double]? = nil) -> ResearchDataset {
        var series = [ResearchSourceSeries(id: "INNOVATION_LEADER", name: "Innovation Leader", sourceColumn: "inno eb",
                                           observations: zip(dates, levels).map { ResearchObservation(date: $0, level: $1) })]
        if let laggard {
            series.append(ResearchSourceSeries(id: "LAGGARD", name: "Laggard", sourceColumn: "laggard",
                observations: zip(dates, laggard).map { ResearchObservation(date: $0, level: $1) }))
        }
        return ResearchDataset(schemaVersion: 1, id: "test", frequency: "monthly", title: "Research",
            period: ResearchSourcePeriod(start: dates.first!, end: dates.last!),
            source: ResearchSource(title: "Rounded source", sha256: "abc", precision: "2 decimals", provenance: "Test", url: "/research/"),
            methodology: [], series: series)
    }
    private func market(_ rows: [Observation], illustrative: Bool = false, status: String = "ok") -> MarketSnapshot {
        MarketSnapshot(generatedAt: "2026-09-01", expenseRatio: 0.0045, series: [
            FundSeries(id: "SPY", name: "SPY", source: "Yahoo Finance", status: status,
                       isIllustrative: illustrative, observations: rows)
        ])
    }
    private func compare(_ dataset: ResearchDataset, _ market: MarketSnapshot? = nil,
                         period: ResearchPeriod = .all) throws -> ResearchResult {
        try ResearchEngine.compare(dataset: dataset, selectedIDs: market == nil ? ["INNOVATION_LEADER"] : ["INNOVATION_LEADER", "SPY"],
                                   snapshot: market, period: period)
    }

    func testResearchLevelsRebaseWithoutInventingDividendsOrFees() throws {
        let result = try compare(source(["2025-01-31", "2025-02-28", "2025-03-31"], [2, 3, 2.5]))
        XCTAssertEqual(result.series[0].points.map(\.value), [100, 150, 125])
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.change), 0.25, accuracy: 1e-12)
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.drawdown), 125.0 / 150 - 1, accuracy: 1e-12)
        XCTAssertNil(result.series[0].metrics.cagr)
    }

    func testDailyExDateContributesBeforeMonthSamplingWithoutDoubleAdjustments() throws {
        let dataset = source(["2026-01-31", "2026-02-28", "2026-03-31"], [1, 1.1, 1.2])
        let rows = [Observation(date: "2026-01-30", marketPrice: 100, adjustedClose: 90),
                    Observation(date: "2026-02-16", marketPrice: 98, distribution: 2, adjustedClose: 300),
                    Observation(date: "2026-02-27", marketPrice: 98, split: 2, adjustedClose: 500),
                    Observation(date: "2026-03-31", marketPrice: 107.8, adjustedClose: 600)]
        let result = try compare(dataset, market(rows))
        let peer = result.series[1]
        XCTAssertEqual(peer.points[1].value, 100, accuracy: 1e-12)
        XCTAssertEqual(peer.points.last!.value, 110, accuracy: 1e-12)
        XCTAssertEqual(try XCTUnwrap(peer.metrics.change), 0.1, accuracy: 1e-12)
        XCTAssertEqual(peer.points[0].date, "2026-01-31")
        XCTAssertEqual(peer.points[0].observedDate, "2026-01-30")
    }

    func testLastSessionWithinFourDaysAndMissingMonthsNeverBackfill() throws {
        let dataset = source(["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"], [1, 2, 3, 4])
        let rows = [Observation(date: "2026-01-26", marketPrice: 100),
                    Observation(date: "2026-02-24", marketPrice: 110),
                    Observation(date: "2026-03-25", marketPrice: 120),
                    Observation(date: "2026-04-30", marketPrice: 130)]
        let result = try compare(dataset, market(rows))
        XCTAssertEqual(result.dates, ["2026-02-28", "2026-04-30"])
        XCTAssertEqual(result.series[1].points[0].observedDate, "2026-02-24")
        XCTAssertEqual(result.series[1].points.last!.value, 130.0 / 110 * 100, accuracy: 1e-12)
        XCTAssertTrue(result.warnings.contains { $0.contains("missing") })
    }

    func testEachSelectedSeriesUsesSameStartAndEndWithoutPreInceptionHistory() throws {
        let dataset = source(["2025-01-31", "2025-02-28", "2025-03-31"], [1, 2, 6])
        let rows = [Observation(date: "2025-02-28", marketPrice: 50), Observation(date: "2025-03-31", marketPrice: 55)]
        let result = try compare(dataset, market(rows))
        XCTAssertEqual(result.start, "2025-02-28")
        XCTAssertEqual(result.series.map { $0.points.first!.value }, [100, 100])
        XCTAssertEqual(result.series[0].points.last!.value, 300)
        XCTAssertEqual(result.series[1].points.last!.value, 110, accuracy: 1e-12)
    }

    func testPartialCurrentMonthCannotMasqueradeAsCompletedMonthEnd() throws {
        let dataset = source(["2026-08-31", "2026-09-30"], [1, 2])
        let fund = FundSeries(id: "SPY", name: "SPY", source: "Yahoo Finance", observations: [
            Observation(date: "2026-08-31", marketPrice: 100),
            Observation(date: "2026-09-28", marketPrice: 110)
        ])
        let partial = MarketSnapshot(generatedAt: "2026-09-29T19:00:00Z", expenseRatio: 0.0045, series: [fund])
        XCTAssertEqual(try compare(dataset, partial).dates, ["2026-08-31"])
        let completed = MarketSnapshot(generatedAt: "2026-09-30T23:00:00Z", expenseRatio: 0.0045, series: [fund])
        let result = try compare(dataset, completed)
        XCTAssertEqual(result.dates, ["2026-08-31", "2026-09-30"])
        XCTAssertEqual(result.series[1].points.last?.observedDate, "2026-09-28")
    }

    func testPeriodIsAppliedAfterSharedWindowAndClampsLeapDay() throws {
        let dates = ["2023-02-28", "2023-03-31", "2024-02-29", "2024-03-31"]
        let dataset = source(dates, [1, 2, 4, 8])
        let rows = [Observation(date: "2023-02-28", marketPrice: 100),
                    Observation(date: "2023-03-31", marketPrice: 101),
                    Observation(date: "2024-02-29", marketPrice: 110)]
        let result = try compare(dataset, market(rows), period: .oneYear)
        XCTAssertEqual(result.start, "2023-02-28")
        XCTAssertEqual(result.end, "2024-02-29")
        XCTAssertNotNil(result.series[0].metrics.cagr)
    }

    func testCAGRUsesElapsed365Point25DaysAndRequiresCalendarYear() throws {
        let exact = try compare(source(["2025-01-31", "2026-01-31"], [1, 2]))
        XCTAssertEqual(try XCTUnwrap(exact.series[0].metrics.cagr), pow(2, 365.25 / 365) - 1, accuracy: 1e-12)
        let partial = try compare(source(["2025-02-28", "2026-01-31"], [1, 2]))
        XCTAssertNil(partial.series[0].metrics.cagr)
        XCTAssertEqual(partial.series[0].metrics.change, 1)
    }

    func testOnlyOneSharedMonthHasNoInventedPerformance() throws {
        let result = try compare(source(["2025-01-31", "2025-02-28"], [1, 2]),
                                 market([Observation(date: "2025-02-28", marketPrice: 100)]))
        XCTAssertEqual(result.dates.count, 1)
        for item in result.series {
            XCTAssertNil(item.metrics.change)
            XCTAssertNil(item.metrics.cagr)
            XCTAssertNil(item.metrics.drawdown)
        }
    }

    func testUnavailableAndIllustrativePeersAreExplicitlyExcluded() throws {
        let dataset = source(["2025-01-31", "2025-02-28"], [1, 2])
        for snapshot in [market([]), market([Observation(date: "2025-01-31", marketPrice: 100)], illustrative: true),
                         market([Observation(date: "2025-01-31", marketPrice: 100)], status: "unavailable")] {
            let result = try compare(dataset, snapshot)
            XCTAssertEqual(result.series.map(\.id), ["INNOVATION_LEADER"])
            XCTAssertTrue(result.warnings.contains { $0.contains("SPY:") && $0.contains("excluded") })
        }
    }

    func testUnknownOrDuplicateSelectionsCannotMasqueradeAsResearch() throws {
        let dataset = source(["2025-01-31", "2025-02-28"], [1, 2])
        for ids in [["REDI"], ["SPY", "SPY"], ["NAV"], ["FICTITIOUS"]] {
            XCTAssertThrowsError(try ResearchEngine.compare(dataset: dataset, selectedIDs: ids))
        }
        XCTAssertEqual(try ResearchEngine.compare(dataset: dataset, selectedIDs: []).series.map(\.id), ["INNOVATION_LEADER"])
    }

    func testMalformedSourceCalendarOrderAndLevelsAreRejected() throws {
        for dates in [["2025-01-30", "2025-02-28"], ["2025-01-31", "2025-02-30"],
                      ["2025-02-28", "2025-01-31"], ["2025-01-31", "2025-01-31"]] {
            XCTAssertThrowsError(try compare(source(dates, [1, 2])))
        }
        for level in [0.0, -1, Double.infinity, .nan] {
            XCTAssertThrowsError(try compare(source(["2025-01-31", "2025-02-28"], [1, level])))
        }
        let valid = source(["2025-01-31", "2025-02-28"], [1, 2])
        let falsePeriod = ResearchDataset(schemaVersion: 1, id: valid.id, frequency: valid.frequency, title: valid.title,
            period: ResearchSourcePeriod(start: valid.period.start, end: "2025-03-31"), source: valid.source,
            methodology: [], series: valid.series)
        XCTAssertThrowsError(try falsePeriod.validated())
    }

    func testBadETFOrderingAndDistributionCannotSilentlyProduceReturns() throws {
        let dataset = source(["2025-01-31", "2025-02-28"], [1, 2])
        let first = Observation(date: "2025-01-31", marketPrice: 100)
        for rows in [[first, first], [Observation(date: "2025-02-28", marketPrice: 100), first],
                     [first, Observation(date: "2025-02-28", marketPrice: 0)],
                     [first, Observation(date: "2025-02-28", marketPrice: 99, distribution: -1)]] {
            XCTAssertThrowsError(try compare(dataset, market(rows)))
        }
    }

    func testBundledWorkbookDataMatchesAuditedClosingLevelsAndElapsedCAGR() throws {
        // The shared source file is outside the package; the app bundles this exact file via generate_project.py.
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let dataset = try JSONDecoder().decode(ResearchDataset.self, from: Data(contentsOf: root.appendingPathComponent("data/strategy_research.json"))).validated()
        let result = try ResearchEngine.compare(dataset: dataset)
        XCTAssertEqual(result.dates.count, 281)
        XCTAssertEqual(result.start, "2003-04-30")
        XCTAssertEqual(result.end, "2026-08-31")
        XCTAssertEqual(result.series[0].points.last!.value, 4808, accuracy: 1e-8)
        XCTAssertEqual(try XCTUnwrap(result.series[0].metrics.cagr), 0.18051499, accuracy: 1e-8)
        XCTAssertEqual(try XCTUnwrap(result.series[1].metrics.cagr), 0.12532858, accuracy: 1e-8)
        XCTAssertEqual(try XCTUnwrap(result.series[2].metrics.cagr), 0.11751737, accuracy: 1e-8)
    }
}
