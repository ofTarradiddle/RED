import Foundation

public struct MarketSnapshot: Codable, Sendable {
    public let schemaVersion: Int
    public let generatedAt: String
    public let marketRefreshAt: String?
    public let lastAttemptAt: String?
    public let status: String
    public let expenseRatio: Double
    public let series: [FundSeries]

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version", generatedAt = "generated_at"
        case marketRefreshAt = "market_refresh_at", lastAttemptAt = "last_attempt_at"
        case status, expenseRatio = "expense_ratio", series
    }

    public init(schemaVersion: Int = 1, generatedAt: String,
                marketRefreshAt: String? = nil, lastAttemptAt: String? = nil,
                status: String = "ok", expenseRatio: Double, series: [FundSeries]) {
        self.schemaVersion = schemaVersion
        self.generatedAt = generatedAt
        self.marketRefreshAt = marketRefreshAt
        self.lastAttemptAt = lastAttemptAt
        self.status = status
        self.expenseRatio = expenseRatio
        self.series = series
    }

    /// A complete validation pass is also applied to unselected funds. Invalid
    /// data is never replaced by zero, carried forward, or silently dropped.
    public func validated() throws -> MarketSnapshot {
        guard schemaVersion == 1 else { throw ComparisonError.invalidSnapshot("Unsupported data format.") }
        guard expenseRatio.isFinite, expenseRatio >= 0, expenseRatio < 1 else {
            throw ComparisonError.invalidSnapshot("The expense ratio is invalid.")
        }
        var identifiers = Set<String>()
        for fund in series {
            guard ComparisonEngine.supportedIDs.contains(fund.id), identifiers.insert(fund.id).inserted else {
                throw ComparisonError.invalidSnapshot("The snapshot has an unknown or repeated fund identifier.")
            }
            guard fund.currency == "USD" else {
                throw ComparisonError.invalidSnapshot("All comparison data must be in USD.")
            }
            if let date = fund.asOf, !TradingDate.isValid(date) {
                throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid closing date.")
            }
            var dates = Set<String>()
            for row in fund.observations {
                guard TradingDate.isValid(row.date), dates.insert(row.date).inserted else {
                    throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid or repeated observation date.")
                }
                guard row.marketPrice.isFinite, row.marketPrice > 0,
                      row.distribution.isFinite, row.distribution >= 0 else {
                    throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid market price or distribution on \(row.date).")
                }
                if let nav = row.nav, (!nav.isFinite || nav <= 0) {
                    throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid NAV on \(row.date).")
                }
                if let split = row.split, (!split.isFinite || split < 0) {
                    throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid split on \(row.date).")
                }
                if let close = row.adjustedClose, (!close.isFinite || close <= 0) {
                    throw ComparisonError.invalidSnapshot("\(fund.id) has an invalid adjusted close on \(row.date).")
                }
            }
        }
        guard identifiers.contains("REDI") else {
            throw ComparisonError.invalidSnapshot("The published snapshot does not include REDI.")
        }
        return self
    }
}

public struct FundSeries: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let currency: String
    public let kind: String
    public let source: String
    public let sourceURL: String?
    public let asOf: String?
    public let status: String
    public let error: String?
    public let isIllustrative: Bool
    public let observations: [Observation]

    enum CodingKeys: String, CodingKey {
        case id, name, currency, kind, source, sourceURL = "source_url", asOf = "as_of"
        case status, error, isIllustrative = "is_illustrative", observations
    }

    public init(id: String, name: String, currency: String = "USD", kind: String = "etf",
                source: String, sourceURL: String? = nil, asOf: String? = nil,
                status: String = "ok", error: String? = nil,
                isIllustrative: Bool = false, observations: [Observation]) {
        self.id = id; self.name = name; self.currency = currency; self.kind = kind
        self.source = source; self.sourceURL = sourceURL; self.asOf = asOf
        self.status = status; self.error = error; self.isIllustrative = isIllustrative
        self.observations = observations
    }
}

public struct Observation: Codable, Sendable {
    public let date: String
    public let marketPrice: Double
    public let nav: Double?
    public let distribution: Double
    public let split: Double?
    public let adjustedClose: Double?

    enum CodingKeys: String, CodingKey {
        case date, marketPrice = "market_price", nav, distribution, split
        case adjustedClose = "adjusted_close"
    }

    public init(date: String, marketPrice: Double, nav: Double? = nil,
                distribution: Double = 0, split: Double? = nil, adjustedClose: Double? = nil) {
        self.date = date; self.marketPrice = marketPrice; self.nav = nav
        self.distribution = distribution; self.split = split; self.adjustedClose = adjustedClose
    }
}

public enum REDIBasis: String, Codable, CaseIterable, Identifiable, Sendable {
    case marketPrice = "market_price", nav
    public var id: String { rawValue }
    public var title: String { self == .nav ? "NAV" : "Market Price" }
}

public enum ReturnMode: String, Codable, CaseIterable, Identifiable, Sendable {
    case price, reinvested
    public var id: String { rawValue }
    public var title: String { self == .price ? "Price change" : "Distributions reinvested" }
}

public enum ComparisonPeriod: String, Codable, CaseIterable, Identifiable, Sendable {
    case oneMonth = "1M", threeMonths = "3M", sixMonths = "6M"
    case yearToDate = "YTD", oneYear = "1Y", all = "ALL"
    public var id: String { rawValue }
    public var title: String { self == .all ? "All" : rawValue }
}

public struct ComparisonSettings: Codable, Equatable, Sendable {
    public var peers: [String]
    public var basis: REDIBasis
    public var returnMode: ReturnMode
    public var period: ComparisonPeriod

    public init(peers: [String] = ["SPY", "ITAN"], basis: REDIBasis = .marketPrice,
                returnMode: ReturnMode = .price, period: ComparisonPeriod = .oneYear) {
        self.peers = peers; self.basis = basis; self.returnMode = returnMode; self.period = period
    }
}

public struct ComparisonResult: Sendable {
    public let series: [ComparedSeries]
    public let dates: [String]
    public let start: String?
    public let end: String?
    public let warnings: [String]
    public let riskReason: String?
}

public struct ComparedSeries: Identifiable, Sendable {
    public let id: String
    public let name: String
    public let isIllustrative: Bool
    public let points: [ComparisonPoint]
    public let metrics: RiskMetrics
}

public struct ComparisonPoint: Sendable {
    public let date: String
    public let value: Double
}

public struct RiskMetrics: Sendable {
    public let change: Double?
    public let drawdown: Double?
    public let volatility: Double?
    public let correlation: Double?
}

public enum ComparisonError: Error, LocalizedError, Sendable {
    case invalidSnapshot(String)
    case invalidSettings(String)
    case calculation(String)

    public var errorDescription: String? {
        switch self {
        case .invalidSnapshot(let message), .invalidSettings(let message), .calculation(let message): return message
        }
    }
}
