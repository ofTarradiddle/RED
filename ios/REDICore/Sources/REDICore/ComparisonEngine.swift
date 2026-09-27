import Foundation

/// Same daily-close methodology as the web comparison. The publisher supplies
/// split-adjusted prices and per-share distributions; adjusted close and split
/// ratios must not be applied again here.
public enum ComparisonEngine {
    public static let supportedIDs: Set<String> = ["REDI", "SPY", "VOO", "QQQ", "ITAN", "SYLD"]
    public static let peerIDs: [String] = ["SPY", "VOO", "QQQ", "ITAN", "SYLD"]

    private struct WealthPoint {
        let date: String
        let wealth: Double
    }
    private struct Prepared {
        let source: FundSeries
        let points: [WealthPoint]
        let index: [String: Double]
    }

    public static func compare(snapshot: MarketSnapshot, settings: ComparisonSettings) throws -> ComparisonResult {
        let snapshot = try snapshot.validated()
        guard Set(settings.peers).count == settings.peers.count,
              settings.peers.allSatisfy({ peerIDs.contains($0) }) else {
            throw ComparisonError.invalidSettings("Select each supported comparison ETF only once.")
        }
        var warnings: [String] = []
        var prepared: [Prepared] = []
        let funds = Dictionary(uniqueKeysWithValues: snapshot.series.map { ($0.id, $0) })
        for id in ["REDI"] + settings.peers {
            guard let fund = funds[id] else {
                warnings.append("\(id): No published history is available.")
                continue
            }
            let points = try buildWealth(fund, settings: settings, warnings: &warnings)
            if points.isEmpty {
                warnings.append("\(id): \(fund.error ?? "No usable observations for this selection.")")
            } else {
                prepared.append(Prepared(source: fund, points: points,
                                         index: Dictionary(uniqueKeysWithValues: points.map { ($0.date, $0.wealth) })))
            }
        }
        guard let redi = prepared.first(where: { $0.source.id == "REDI" }) else {
            return empty(warnings: warnings + ["REDI history is not available for this selection."])
        }
        // Build each complete distribution chain first. Calendar alignment must
        // never remove a dividend simply because a peer is missing its ex-date.
        var dates = redi.points.map(\.date).filter { date in prepared.allSatisfy { $0.index[date] != nil } }
        guard let commonEnd = dates.last else {
            return empty(warnings: warnings + ["The selected funds do not yet share a closing date."])
        }
        if let cutoff = TradingDate.cutoff(end: commonEnd, period: settings.period) {
            let yearBase = settings.period == .yearToDate ? dates.last(where: { $0 < cutoff }) : nil
            dates = dates.filter { $0 >= cutoff || $0 == yearBase }
        }
        guard let start = dates.first, let end = dates.last else { return empty(warnings: warnings) }
        let peers = prepared.filter { $0.source.id != "REDI" }
        let calendars = peers.isEmpty ? prepared : peers
        let exchangeDates = Set(calendars.flatMap { $0.points.map(\.date) }.filter { $0 >= start && $0 <= end })
        let hasMissingSession = exchangeDates.count > dates.count
        let hasLongGap = zip(dates, dates.dropFirst()).contains { TradingDate.days(from: $0, to: $1) > 5 }
        let riskAvailable = dates.count >= 21 && !hasMissingSession && !hasLongGap
        let riskReason: String?
        if dates.count < 21 {
            riskReason = "At least 20 matched daily returns are needed for volatility and correlation."
        } else if hasMissingSession || hasLongGap {
            riskReason = "Volatility and correlation are withheld because the matched daily history has gaps."
        } else { riskReason = nil }

        let histories = try prepared.map { item -> (Prepared, [ComparisonPoint], [Double], Double) in
            let base = item.index[start]!
            let points = dates.map { ComparisonPoint(date: $0, value: item.index[$0]! / base * 100) }
            guard points.allSatisfy({ $0.value.isFinite && $0.value > 0 }) else {
                throw ComparisonError.calculation("\(item.source.id) cannot be normalized safely.")
            }
            let returns = zip(points, points.dropFirst()).map { $1.value / $0.value - 1 }
            var peak = 100.0, drawdown = 0.0
            for point in points {
                peak = max(peak, point.value)
                drawdown = min(drawdown, point.value / peak - 1)
            }
            return (item, points, returns, drawdown)
        }
        let rediReturns = histories.first { $0.0.source.id == "REDI" }!.2
        let compared = histories.map { item, points, returns, drawdown in
            let volatility = riskAvailable ? sampleVariance(returns).map { sqrt($0 * 252) } : nil
            return ComparedSeries(
                id: item.source.id, name: item.source.name, isIllustrative: item.source.isIllustrative,
                points: points,
                metrics: RiskMetrics(change: points.count > 1 ? points.last!.value / 100 - 1 : nil,
                                     drawdown: points.count > 1 ? drawdown : nil,
                                     volatility: volatility,
                                     correlation: riskAvailable ? correlation(returns, rediReturns) : nil)
            )
        }
        if dates.count == 1 { warnings.append("Only one shared closing date is available; performance needs at least two.") }
        return ComparisonResult(series: compared, dates: dates, start: start, end: end,
                                warnings: warnings, riskReason: riskReason)
    }

    private static func empty(warnings: [String]) -> ComparisonResult {
        ComparisonResult(series: [], dates: [], start: nil, end: nil, warnings: warnings, riskReason: nil)
    }

    private static func buildWealth(_ series: FundSeries, settings: ComparisonSettings,
                                   warnings: inout [String]) throws -> [WealthPoint] {
        let usesNAV = series.id == "REDI" && settings.basis == .nav
        let observations = series.observations.sorted { $0.date < $1.date }
        var rows: [(Observation, Double)] = []
        var omitted = false
        for row in observations {
            guard let price = usesNAV ? row.nav : row.marketPrice else {
                if settings.returnMode == .reinvested && row.distribution > 0 {
                    warnings.append("\(series.id): Reinvested performance is unavailable because a distribution or its ex-date price is missing.")
                    return []
                }
                omitted = true
                continue
            }
            rows.append((row, price))
        }
        if omitted { warnings.append("\(series.id): A date without a valid NAV was omitted.") }
        var wealth = 1.0
        var points: [WealthPoint] = []
        for (index, pair) in rows.enumerated() {
            if index > 0 {
                let dividend = settings.returnMode == .reinvested ? pair.0.distribution : 0
                wealth *= (pair.1 + dividend) / rows[index - 1].1
            }
            guard wealth.isFinite, wealth > 0 else {
                throw ComparisonError.calculation("\(series.id) has an unusable cumulative return.")
            }
            points.append(WealthPoint(date: pair.0.date, wealth: wealth))
        }
        return points
    }

    private static func sampleVariance(_ values: [Double]) -> Double? {
        guard values.count >= 2 else { return nil }
        let mean = values.reduce(0, +) / Double(values.count)
        return values.reduce(0) { $0 + pow($1 - mean, 2) } / Double(values.count - 1)
    }

    private static func correlation(_ left: [Double], _ right: [Double]) -> Double? {
        guard left.count == right.count, left.count >= 20 else { return nil }
        let leftMean = left.reduce(0, +) / Double(left.count)
        let rightMean = right.reduce(0, +) / Double(right.count)
        var numerator = 0.0, leftSquares = 0.0, rightSquares = 0.0
        for (l, r) in zip(left, right) {
            let dl = l - leftMean, dr = r - rightMean
            numerator += dl * dr; leftSquares += dl * dl; rightSquares += dr * dr
        }
        guard leftSquares >= 1e-24, rightSquares >= 1e-24 else { return nil }
        return max(-1, min(1, numerator / sqrt(leftSquares * rightSquares)))
    }
}
