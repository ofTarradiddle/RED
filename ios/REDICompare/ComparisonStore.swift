import Foundation
import SwiftUI
import REDICore

struct SavedComparison: Identifiable, Codable, Equatable {
    let id: UUID
    var name: String
    var settings: ComparisonSettings
}

@MainActor
final class ComparisonStore: ObservableObject {
    nonisolated static let dataEndpoint = URL(string: "https://oftarradiddle.github.io/RED/compare/data.json")!
    private static let preferencesKey = "hetzerk.native.comparison.settings.v1"
    private static let savedKey = "hetzerk.native.comparison.saved.v1"
    private static let allowedPeers = ["SPY", "VOO", "QQQ", "ITAN", "SYLD"]

    @Published var snapshot: MarketSnapshot?
    @Published var settings: ComparisonSettings {
        didSet {
            if let encoded = try? JSONEncoder().encode(settings) {
                defaults.set(encoded, forKey: Self.preferencesKey)
            }
            recalculate()
        }
    }
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isUsingCache = false
    @Published var result: REDICore.ComparisonResult?
    @Published var savedComparisons: [SavedComparison]

    private let defaults: UserDefaults
    private let cacheURL: URL
    private let endpoint: URL
    private let usesFixture: Bool
    private var snapshotPersisted = false

    init(defaults: UserDefaults = .standard, cacheURL: URL? = nil,
         endpoint: URL = ComparisonStore.dataEndpoint, fixtureURL: URL? = nil) {
        self.defaults = defaults
        self.endpoint = endpoint
        self.usesFixture = fixtureURL != nil
        let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        self.cacheURL = cacheURL ?? directory.appendingPathComponent("HetzerkCompare", isDirectory: true)
            .appendingPathComponent("market-snapshot.json")
        if let raw = defaults.data(forKey: Self.preferencesKey),
           let saved = try? JSONDecoder().decode(ComparisonSettings.self, from: raw) {
            self.settings = Self.normalized(saved)
        } else {
            self.settings = ComparisonSettings()
        }
        if let raw = defaults.data(forKey: Self.savedKey),
           let saved = try? JSONDecoder().decode([SavedComparison].self, from: raw) {
            var seen = Set<UUID>()
            self.savedComparisons = saved.filter { seen.insert($0.id).inserted }.prefix(20).map {
                SavedComparison(id: $0.id, name: String($0.name.prefix(60)), settings: Self.normalized($0.settings))
            }
        } else {
            self.savedComparisons = []
        }
        if let raw = try? Data(contentsOf: fixtureURL ?? self.cacheURL),
           let decoded = try? JSONDecoder().decode(MarketSnapshot.self, from: raw),
           let valid = try? decoded.validated() {
            self.snapshot = valid
            self.isUsingCache = fixtureURL == nil
            self.snapshotPersisted = fixtureURL == nil
        }
        recalculate()
    }

    private static func normalized(_ input: ComparisonSettings) -> ComparisonSettings {
        var output = input
        var seen = Set<String>()
        output.peers = Array(input.peers.filter { allowedPeers.contains($0) && seen.insert($0).inserted }.prefix(3))
        return output
    }

    func updateSettings(_ change: (inout ComparisonSettings) -> Void) {
        var next = settings
        change(&next)
        settings = Self.normalized(next)
    }

    func refresh() async {
        guard !isLoading, !usesFixture else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            var request = URLRequest(url: endpoint, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 25)
            request.setValue("application/json", forHTTPHeaderField: "Accept")
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw SnapshotError.unavailable
            }
            guard data.count <= 20_000_000,
                  response.mimeType == "application/json" || response.mimeType == "text/plain" else {
                throw SnapshotError.invalidResponse
            }
            let decoded = try JSONDecoder().decode(MarketSnapshot.self, from: data).validated()
            try Task.checkCancellation()
            // Validate completely before replacing a known-good offline snapshot.
            let comparison = try ComparisonEngine.compare(snapshot: decoded, settings: settings)
            snapshot = decoded
            snapshotPersisted = false
            result = comparison
            isUsingCache = false
            errorMessage = nil
            do {
                try FileManager.default.createDirectory(at: cacheURL.deletingLastPathComponent(), withIntermediateDirectories: true)
                try data.write(to: cacheURL, options: .atomic)
                snapshotPersisted = true
                var file = cacheURL
                var attributes = URLResourceValues()
                attributes.isExcludedFromBackup = true
                try? file.setResourceValues(attributes)
            } catch {
                errorMessage = "Data is up to date, but this device could not save it for offline use."
            }
        } catch is CancellationError {
            return
        } catch {
            isUsingCache = snapshotPersisted
            errorMessage = snapshot == nil
                ? "The daily snapshot could not be loaded. Connect to the internet and try again."
                : "Could not check for updates. Your last loaded snapshot remains available; check its source dates."
        }
    }

    private func recalculate() {
        guard let snapshot else { result = nil; return }
        do {
            result = try ComparisonEngine.compare(snapshot: snapshot, settings: settings)
        } catch {
            result = nil
            errorMessage = "This selection could not be calculated from the published observations."
        }
    }

    func saveComparison(name: String) {
        let text = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let label = text.isEmpty ? (["REDI"] + settings.peers).joined(separator: " / ") : text
        savedComparisons.insert(SavedComparison(id: UUID(), name: String(label.prefix(60)), settings: settings), at: 0)
        savedComparisons = Array(savedComparisons.prefix(20))
        persistSaved()
    }

    func loadComparison(_ item: SavedComparison) { settings = Self.normalized(item.settings) }
    func removeComparison(id: UUID) {
        savedComparisons.removeAll { $0.id == id }
        persistSaved()
    }
    private func persistSaved() {
        if let data = try? JSONEncoder().encode(savedComparisons) { defaults.set(data, forKey: Self.savedKey) }
    }

    var shareSummary: String {
        guard let result, !result.series.isEmpty else { return "REDI Compare · Hetzerk Asset Management" }
        let lines = result.series.map { series -> String in
            let change = series.metrics.change.map { String(format: "%+.2f%%", $0 * 100) } ?? "Unavailable"
            return "\(series.id)\(series.isIllustrative ? " (illustrative)" : ""): \(change)"
        }
        let qualification = snapshot?.series.contains(where: { $0.id == "REDI" && $0.isIllustrative }) == true
            ? "\nREDI is illustrative prelaunch data, not an actual fund track record." : ""
        let retained = snapshot?.series.filter { (["REDI"] + settings.peers).contains($0.id) && $0.status != "ok" }
            .map { "\($0.id): source update unavailable; observations through \($0.asOf ?? "unavailable")." } ?? []
        let sourceNote = retained.isEmpty ? "" : "\n" + retained.joined(separator: "\n")
        return "REDI Compare · Hetzerk Asset Management\n\(result.start ?? "—") – \(result.end ?? "—")\n\(settings.basis.title) · \(settings.returnMode.title)\n\(lines.joined(separator: "\n"))\(qualification)\(sourceNote)\nDaily closing data. Past performance does not guarantee future results.\nhttps://oftarradiddle.github.io/RED/compare/"
    }

    private enum SnapshotError: Error { case unavailable, invalidResponse }
}
