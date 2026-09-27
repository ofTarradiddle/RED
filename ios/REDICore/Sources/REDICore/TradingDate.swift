import Foundation

enum TradingDate {
    static var calendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        calendar.locale = Locale(identifier: "en_US_POSIX")
        return calendar
    }

    static func parse(_ value: String) -> Date? {
        let bytes = Array(value.utf8)
        guard bytes.count == 10, bytes[4] == 45, bytes[7] == 45,
              bytes.enumerated().allSatisfy({ [4, 7].contains($0.offset) || (48...57).contains($0.element) }),
              let year = Int(value.prefix(4)), let month = Int(value.dropFirst(5).prefix(2)),
              let day = Int(value.suffix(2)), year >= 1 else { return nil }
        let parts = DateComponents(year: year, month: month, day: day)
        guard let date = calendar.date(from: parts),
              calendar.dateComponents([.year, .month, .day], from: date) == parts else { return nil }
        return date
    }

    static func isValid(_ value: String) -> Bool { parse(value) != nil }

    static func string(_ date: Date) -> String {
        let parts = calendar.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", parts.year!, parts.month!, parts.day!)
    }

    static func cutoff(end: String, period: ComparisonPeriod) -> String? {
        guard let date = parse(end), period != .all else { return nil }
        if period == .yearToDate { return String(end.prefix(4)) + "-01-01" }
        let months: Int
        switch period {
        case .oneMonth: months = 1
        case .threeMonths: months = 3
        case .sixMonths: months = 6
        case .oneYear: months = 12
        default: return nil
        }
        return calendar.date(byAdding: .month, value: -months, to: date).map(string)
    }

    static func days(from start: String, to end: String) -> Double {
        guard let first = parse(start), let last = parse(end) else { return .infinity }
        return last.timeIntervalSince(first) / 86_400
    }
}
