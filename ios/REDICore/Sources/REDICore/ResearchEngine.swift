import Foundation

/// Source-reported hypothetical research is deliberately separate from FundSeries and REDI NAV.
public struct ResearchDataset: Codable, Sendable {
    public let schemaVersion: Int
    public let id: String
    public let frequency: String
    public let title: String
    public let period: ResearchSourcePeriod
    public let source: ResearchSource
    public let methodology: [String]
    public let series: [ResearchSourceSeries]
    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case id, frequency, title, period, source, methodology, series
    }

    public func validated() throws -> ResearchDataset {
        guard schemaVersion == 1, frequency == "monthly", !id.isEmpty,
              ResearchEngine.monthEnd(period.start) == period.start,
              ResearchEngine.monthEnd(period.end) == period.end,
              period.start < period.end, !series.isEmpty,
              series.contains(where: { $0.id == "INNOVATION_LEADER" }),
              Set(series.map(\.id)).count == series.count else {
            throw ResearchError.invalidSource("Unsupported or incomplete monthly research dataset.")
        }
        for item in series {
            guard ResearchEngine.researchIDs.contains(item.id), !item.name.isEmpty,
                  item.observations.first?.date == period.start,
                  item.observations.last?.date == period.end else {
                throw ResearchError.invalidSource("\(item.id): observations do not match the stated source period.")
            }
            var previous = ""
            for row in item.observations {
                guard row.date > previous, row.date >= period.start, row.date <= period.end,
                      ResearchEngine.monthEnd(row.date) == row.date,
                      row.level.isFinite, row.level > 0 else {
                    throw ResearchError.invalidSource("\(item.id): invalid or repeated month-end level.")
                }
                previous = row.date
            }
        }
        return self
    }
}

public struct ResearchSourcePeriod: Codable, Sendable {
    public let start: String
    public let end: String
}
public struct ResearchSource: Codable, Sendable {
    public let title: String
    public let sha256: String
    public let precision: String
    public let provenance: String
    public let url: String
}
public struct ResearchSourceSeries: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let sourceColumn: String
    public let observations: [ResearchObservation]
    enum CodingKeys: String, CodingKey { case id, name, sourceColumn = "source_column", observations }
}
public struct ResearchObservation: Codable, Sendable {
    public let date: String
    public let level: Double
}
public enum ResearchPeriod: String, CaseIterable, Identifiable, Sendable {
    case all, oneYear, fiveYears, tenYears
    public var id: String { rawValue }
    public var title: String {
        switch self { case .all: return "All"; case .oneYear: return "1Y"; case .fiveYears: return "5Y"; case .tenYears: return "10Y" }
    }
    var months: Int? {
        switch self { case .all: return nil; case .oneYear: return 12; case .fiveYears: return 60; case .tenYears: return 120 }
    }
}
public struct ResearchPoint: Codable, Sendable {
    /// Calendar month end shared by the chart; observedDate retains the actual ETF session.
    public let date: String
    public let value: Double
    public let observedDate: String
}
public struct ResearchMetrics: Codable, Sendable {
    public let change: Double?
    public let cagr: Double?
    public let drawdown: Double?
}
public struct ResearchComparedSeries: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let isResearch: Bool
    public let points: [ResearchPoint]
    public let metrics: ResearchMetrics
}
public struct ResearchResult: Codable, Sendable {
    public let dates: [String]
    public let series: [ResearchComparedSeries]
    public let warnings: [String]
    public var start: String? { dates.first }
    public var end: String? { dates.last }
}
public enum ResearchError: LocalizedError {
    case invalidSource(String)
    public var errorDescription: String? {
        switch self { case .invalidSource(let message): return message }
    }
}

public enum ResearchEngine {
    public static let researchIDs = ["INNOVATION_LEADER", "LAGGARD", "MARKET_BACKTEST", "MARKET_EQUAL_WEIGHT", "NON_RD"]
    public static let defaultSelection = ["INNOVATION_LEADER", "LAGGARD", "MARKET_BACKTEST"]
    public static let allowedETFs = ["SPY", "VOO", "QQQ", "ITAN", "SYLD"]

    /// Build ETF wealth over every supplied session BEFORE monthly sampling or common-date filtering.
    /// Prices and distributions are already split-adjusted; adjustedClose and splits are not applied again.
    public static func compare(dataset: ResearchDataset, selectedIDs: [String] = defaultSelection,
                               snapshot: MarketSnapshot? = nil, period: ResearchPeriod = .all) throws -> ResearchResult {
        let dataset = try dataset.validated()
        guard Set(selectedIDs).count == selectedIDs.count,
              selectedIDs.allSatisfy({ (researchIDs + allowedETFs).contains($0) }) else {
            throw ResearchError.invalidSource("Unknown or repeated research comparison selection.")
        }
        let selectedIDs = selectedIDs.contains("INNOVATION_LEADER") ? selectedIDs : ["INNOVATION_LEADER"] + selectedIDs
        struct History {
            let id: String
            let name: String
            let isResearch: Bool
            let points: [String: ResearchPoint]
        }
        var histories: [History] = []
        var warnings: [String] = []
        let publishedDay = String((snapshot?.generatedAt ?? "").prefix(10))
        let completedThrough = TradingDate.isValid(publishedDay) ? publishedDay : TradingDate.string(Date())
        for id in selectedIDs {
            if let item = dataset.series.first(where: { $0.id == id }) {
                let points = Dictionary(uniqueKeysWithValues: item.observations.map {
                    ($0.date, ResearchPoint(date: $0.date, value: $0.level, observedDate: $0.date))
                })
                histories.append(History(id: id, name: item.name, isResearch: true, points: points))
            } else if allowedETFs.contains(id),
                      let fund = snapshot?.series.first(where: { $0.id == id }),
                      !fund.isIllustrative, fund.currency == "USD", fund.kind == "etf", fund.status != "unavailable", !fund.observations.isEmpty {
                let rows = fund.observations
                var wealth = 1.0
                var previous: Observation?
                var points: [String: ResearchPoint] = [:]
                for row in rows {
                    guard let end = monthEnd(row.date), row.marketPrice.isFinite, row.marketPrice > 0,
                          row.distribution.isFinite, row.distribution >= 0,
                          previous == nil || previous!.date < row.date else {
                        throw ResearchError.invalidSource("\(id): invalid or repeated market observation.")
                    }
                    if let previous { wealth *= (row.marketPrice + row.distribution) / previous.marketPrice }
                    guard wealth.isFinite, wealth > 0 else { throw ResearchError.invalidSource("\(id): invalid reinvested wealth.") }
                    if end <= completedThrough && TradingDate.days(from: row.date, to: end) <= 4 {
                        points[end] = ResearchPoint(date: end, value: wealth, observedDate: row.date)
                    }
                    previous = row
                }
                if points.isEmpty { warnings.append("\(id): no usable completed month-end observations; excluded.") }
                else {
                    histories.append(History(id: id, name: id, isResearch: false, points: points))
                    if fund.status != "ok" { warnings.append("\(id): the latest source update failed; retained history is shown.") }
                }
            } else { warnings.append("\(id): non-illustrative ETF history is unavailable; excluded.") }
        }
        guard histories.contains(where: { $0.id == "INNOVATION_LEADER" }) else {
            return ResearchResult(dates: [], series: [], warnings: warnings + ["Innovation Leader history is unavailable."])
        }
        var common = Set(histories[0].points.keys)
        for history in histories.dropFirst() { common.formIntersection(history.points.keys) }
        var dates = common.sorted()
        if let end = dates.last, let months = period.months, let lastDate = TradingDate.parse(end),
           let cutoff = TradingDate.calendar.date(byAdding: .month, value: -months, to: lastDate) {
            let boundary = TradingDate.string(cutoff)
            dates = dates.filter { $0 >= boundary }
        }
        guard let start = dates.first, let end = dates.last else {
            return ResearchResult(dates: [], series: [], warnings: warnings + ["The selected histories have no shared month-end observations."])
        }
        if start > dataset.period.start || end < dataset.period.end {
            warnings.append("Shared window: \(start) to \(end). All selected series use the same available months; missing history is not filled.")
        }
        if dates.count < 2 { warnings.append("At least two shared month ends are required to calculate returns.") }
        let firstParts = TradingDate.calendar.dateComponents([.year, .month], from: TradingDate.parse(start)!)
        let lastParts = TradingDate.calendar.dateComponents([.year, .month], from: TradingDate.parse(end)!)
        let expectedMonths = (lastParts.year! - firstParts.year!) * 12 + lastParts.month! - firstParts.month! + 1
        if dates.count < expectedMonths {
            warnings.append("Some month ends are missing. Drawdown uses only matched month-end observations and may understate declines.")
        }
        let compared = histories.map { history -> ResearchComparedSeries in
            let baseline = history.points[start]!.value
            let points = dates.map { date -> ResearchPoint in
                let row = history.points[date]!
                return ResearchPoint(date: date, value: row.value / baseline * 100, observedDate: row.observedDate)
            }
            let ratio = history.points[end]!.value / baseline
            let years = TradingDate.days(from: start, to: end) / 365.25
            var peak = 100.0, drawdown = 0.0
            for point in points { peak = max(peak, point.value); drawdown = min(drawdown, point.value / peak - 1) }
            let hasReturn = dates.count >= 2 && years > 0
            let yearCutoff = TradingDate.calendar.date(byAdding: .month, value: -12, to: TradingDate.parse(end)!)!
            let canAnnualize = hasReturn && start <= TradingDate.string(yearCutoff)
            return ResearchComparedSeries(id: history.id, name: history.name, isResearch: history.isResearch, points: points,
                metrics: ResearchMetrics(change: hasReturn ? ratio - 1 : nil,
                                         cagr: canAnnualize ? pow(ratio, 1 / years) - 1 : nil,
                                         drawdown: hasReturn ? drawdown : nil))
        }
        return ResearchResult(dates: dates, series: compared, warnings: warnings)
    }

    static func monthEnd(_ value: String) -> String? {
        guard let date = TradingDate.parse(value), let range = TradingDate.calendar.range(of: .day, in: .month, for: date) else { return nil }
        return String(value.prefix(8)) + String(format: "%02d", range.count)
    }
}
