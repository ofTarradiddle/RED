import Foundation
import JavaScriptCore
import SwiftUI
import REDICore

struct AnnualCoverage: Decodable {
    var complete: Bool
    var required: Int
    var observed: Int
    var missingDates: [String]
    var reason: String?
}
struct AnnualMetricSource: Decodable {
    var filed: String?
    var form: String?
    var fiscalPeriodEnd: String?
    var periodStart: String?
    var sourceUrl: String?
    var unit: String?
}
struct AnnualThemeExcerpt: Decodable {
    var label: String
    var excerpt: String?
    var note: String?
}
struct AnnualFiling: Decodable, Identifiable {
    var form: String?
    var filed: String
    var reportDate: String?
    var accession: String?
    var url: String?
    var status: String?
    var investmentThemes: [AnnualThemeExcerpt]
    var focusAreas: [String]
    var focusNote: String?
    var id: String { accession ?? filed + (form ?? "") }
}
struct AnnualValuation: Decodable {
    var pe: Double?
    var asOf: String
    var note: String?
    var sourceUrl: String?
}
struct AnnualFinancials: Decodable {
    var decisionCutoff: String
    var availableAt: String
    var fiscalPeriodEnd: String
    var metrics: [String: Double?]
    var metricSources: [String: AnnualMetricSource]
    var filings: [AnnualFiling]
    var valuation: AnnualValuation?
    var status: String
    var reason: String?
    func value(_ key: String) -> Double? { metrics[key] ?? nil }
}
struct AnnualCompany: Decodable, Identifiable {
    var id: String
    var name: String
    var ticker: String?
    var sector: String?
    var identityNote: String?
    var financials: AnnualFinancials?
    var canInvest: Bool
    var coverage: AnnualCoverage
    var currentWeight: Double
}
struct AnnualUniverseCoverage: Decodable { var eligible: Int; var supported: Int }
struct AnnualCard: Decodable {
    var year: Int
    var cutoff: String
    var executionDate: String
    var endDate: String
    var round: Int
    var rounds: Int
    var capital: Double
    var companies: [AnnualCompany]
    var disclosure: String
    var coverage: AnnualUniverseCoverage
}
struct AnnualHistoryPoint: Decodable, Identifiable {
    var date: String
    var value: Double
    var cash: Double?
    var investedValue: Double?
    var id: String { date }
}
struct AnnualAttribution: Decodable, Identifiable {
    var id: String
    var name: String
    var ticker: String?
    var totalInvested: Double
    var realizedProfit: Double
    var unrealizedProfit: Double
    var currentValue: Double
    var periods: Int
    var profit: Double
    var contribution: Double
    var returnOnAllocatedCapital: Double?
}
struct AnnualBenchmark: Decodable {
    var id: String
    var status: String
    var reason: String?
    var value: Double?
    var change: Double?
    var path: [AnnualHistoryPoint]
}
struct AnnualBook: Decodable {
    var date: String
    var value: Double
    var cash: Double
    var investedValue: Double
    var change: Double
    var profit: Double
    var companies: [AnnualAttribution]
    var history: [AnnualHistoryPoint]
    var benchmark: AnnualBenchmark?
}
struct AnnualContribution: Decodable, Identifiable {
    var id: String
    var name: String
    var ticker: String?
    var weight: Double
    var invested: Double
    var endingValue: Double
    var profit: Double
    var periodReturn: Double
    var contribution: Double
    enum CodingKeys: String, CodingKey {
        case id, name, ticker, weight, invested, endingValue, profit, contribution
        case periodReturn = "return"
    }
}
struct AnnualResult: Decodable {
    var year: Int
    var cutoff: String
    var from: String
    var to: String
    var before: Double
    var after: Double
    var change: Double
    var profit: Double
    var cashWeight: Double
    var companies: [AnnualContribution]
    var path: [AnnualHistoryPoint]
    var frequency: String
    var partial: Bool
}
struct AnnualOutcome: Decodable, Identifiable {
    var id: String
    var name: String
    var ticker: String?
    var coverage: AnnualCoverage
    var periodReturn: Double?
    enum CodingKeys: String, CodingKey { case id, name, ticker, coverage; case periodReturn = "return" }
}
struct AnnualOutcomes: Decodable { var year: Int; var from: String; var to: String; var companies: [AnnualOutcome] }
struct AnnualScore: Decodable {
    var datasetId: String
    var runId: String
    var status: String
    var startDate: String
    var endDate: String
    var periods: Int
    var finalValue: Double
    var change: Double
    var maxDrawdown: Double
    var benchmarkValue: Double?
}
struct AnnualSnapshot: Decodable {
    var index: Int
    var rounds: Int
    var status: String
    var card: AnnualCard?
    var book: AnnualBook
    var result: AnnualResult?
    var score: AnnualScore?
    var outcomes: AnnualOutcomes?
}
struct AnnualOwnedPeriod: Decodable, Identifiable {
    var year: Int
    var from: String
    var to: String
    var invested: Double
    var endingValue: Double
    var profit: Double
    var periodReturn: Double
    var closed: Bool
    var id: Int { year }
    enum CodingKeys: String, CodingKey { case year, from, to, invested, endingValue, profit, closed; case periodReturn = "return" }
}
struct AnnualCompanyPoint: Decodable, Identifiable {
    var date: String
    var profit: Double
    var contribution: Double
    var value: Double
    var capitalAllocated: Double
    var invested: Bool
    var id: String { date }
}
struct AnnualCompanyHistory: Decodable {
    var id: String
    var name: String
    var ticker: String?
    var periods: [AnnualOwnedPeriod]
    var path: [AnnualCompanyPoint]
    var summary: AnnualAttribution?
    var ownedReturn: Double?
    var ownedReturnPath: [AnnualHistoryPoint]
    var mostRecentPeriod: AnnualCompanyPeriod?
}
struct AnnualCompanyPeriod: Decodable {
    var year: Int
    var cutoff: String
    var from: String
    var to: String
    var name: String
    var ticker: String?
    var coverage: AnnualCoverage
    var periodReturn: Double?
    var path: [AnnualHistoryPoint]
    var benchmark: AnnualPeriodBenchmark?
    enum CodingKeys: String, CodingKey {
        case year, cutoff, from, to, name, ticker, coverage, path, benchmark
        case periodReturn = "return"
    }
}
struct AnnualPeriodBenchmark: Decodable {
    var id: String
    var status: String
    var reason: String?
    var periodReturn: Double?
    var path: [AnnualHistoryPoint]
    enum CodingKeys: String, CodingKey {
        case id, status, reason, path
        case periodReturn = "return"
    }
}
struct AnnualValidation: Decodable { var valid: Bool; var totalWeight: Double?; var cashWeight: Double?; var errors: [String] }
struct AnnualSavedScore: Codable, Identifiable { var id: String; var edition: String; var replay: String; var date: Date }
struct AnnualVerifiedScore: Identifiable { var id: String; var date: Date; var score: AnnualScore }

/// JavaScriptCore allows serialized access from different threads. Bootstrap
/// owns this context exclusively until handing it to the main-actor store.
private struct AnnualBootstrap: @unchecked Sendable {
    let context: JSContext
    let snapshot: AnnualSnapshot
    let asOf: String
    let restored: Bool
    let warning: String?
}

@MainActor
final class AnnualGameStore: ObservableObject {
    enum Screen: Equatable { case menu, decision, reveal, finish }
    @Published var screen: Screen = .menu
    @Published var snapshot: AnnualSnapshot?
    @Published var draft: [String: Double] = [:]
    @Published var validation: AnnualValidation?
    @Published var isReady = false
    @Published var isLoading = true
    @Published var hasSave = false
    @Published var error: String?
    @Published var records: [AnnualVerifiedScore] = []
    @Published var asOf = ""
    private var context: JSContext?
    private var jsError: String?
    private let defaults: UserDefaults
    private let saveKey = "hetzerk.annual.replay.v1"
    private let revealKey = "hetzerk.annual.reveal.v1"
    private let draftKey = "hetzerk.annual.draft.v1"
    private let scoresKey = "hetzerk.annual.scores.v1"

    init(defaults customDefaults: UserDefaults? = nil) {
        if let customDefaults { defaults = customDefaults }
        else {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--ui-testing") {
            defaults = UserDefaults(suiteName: "com.hetzerk.annual.UITests")!
            defaults.removePersistentDomain(forName: "com.hetzerk.annual.UITests")
        } else { defaults = .standard }
        #else
        defaults = .standard
        #endif
        }
        guard let engineURL = Bundle.main.url(forResource: "annual-portfolio-engine", withExtension: "js"),
              let dataURL = Bundle.main.url(forResource: "annual-game", withExtension: "json") else {
            isLoading = false; error = "The bundled annual portfolio archive is missing from this app build."; return
        }
        let saved = defaults.string(forKey: saveKey)
        Task { [weak self] in
            guard let self else { return }
            do {
                let loaded = try await Task.detached(priority: .userInitiated) {
                    try Self.bootstrap(engineURL: engineURL, dataURL: dataURL, saved: saved)
                }.value
                context = loaded.context
                context?.exceptionHandler = { [weak self] _, value in self?.jsError = value?.toString() }
                snapshot = loaded.snapshot; asOf = loaded.asOf; hasSave = loaded.restored; error = loaded.warning
                if hasSave, let bytes = defaults.data(forKey: draftKey), let saved = try? JSONDecoder().decode([String: Double].self, from: bytes) {
                    let eligible = Set(snapshot?.card?.companies.filter(\.canInvest).map(\.id) ?? [])
                    draft = saved.filter { eligible.contains($0.key) && $0.value.isFinite && (0...1).contains($0.value) }
                }
                validateDraft(); verifyScores(); isReady = true; isLoading = false
            } catch { self.error = error.localizedDescription; isLoading = false }
        }
    }

    private enum AnnualError: LocalizedError {
        case message(String)
        var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
    }
    private nonisolated static func bootstrap(engineURL: URL, dataURL: URL, saved: String?) throws -> AnnualBootstrap {
        let engineBytes = try Data(contentsOf: engineURL), datasetBytes = try Data(contentsOf: dataURL)
        guard let engineText = String(data: engineBytes, encoding: .utf8),
              let datasetText = String(data: datasetBytes, encoding: .utf8) else {
            throw AnnualError.message("The bundled annual source is not valid UTF-8.")
        }
        guard let runtime = JSContext() else { throw AnnualError.message("The annual game engine could not start.") }
        var message: String?
        runtime.exceptionHandler = { _, value in message = value?.toString() }
        func evaluate(_ script: String) throws -> JSValue {
            message = nil
            guard let value = runtime.evaluateScript(script), message == nil else { throw AnnualError.message(message ?? "The annual source could not load.") }
            return value
        }
        _ = try evaluate(engineText)
        let manifestURL = dataURL.deletingLastPathComponent().appendingPathComponent("annual-game-manifest.json")
        let manifestBytes = try? Data(contentsOf: manifestURL)
        let engineVersion = Int(try evaluate("AnnualPortfolio.VERSION").toInt32())
        let verifiedID = AnnualBundleManifest.verifiedDatasetID(manifestData: manifestBytes,
            engineData: engineBytes, datasetData: datasetBytes, engineVersion: engineVersion)
        runtime.setObject(datasetText, forKeyedSubscript: "annualText" as NSString)
        _ = try evaluate("var annualData=JSON.parse(annualText); annualText=null; var annual=AnnualPortfolio; var annualRun;")
        if let verifiedID {
            runtime.setObject(verifiedID, forKeyedSubscript: "annualVerifiedEdition" as NSString)
            _ = try evaluate("annualRun=annual.createWithVerifiedEdition(annualData,annualVerifiedEdition); annualVerifiedEdition=null;")
        } else {
            _ = try evaluate("annualRun=annual.create(annualData)")
        }
        var restored = false, warning: String?
        if let saved {
            runtime.setObject(saved, forKeyedSubscript: "annualSave" as NSString)
            do { _ = try evaluate("annualRun=annual.restore(annualData,annualSave)"); restored = true }
            catch { warning = "Your previous run belongs to another data edition. Start a new portfolio for this source archive." }
        }
        let expression = """
        JSON.stringify({index:annualRun.index,rounds:annualRun.rounds,status:annualRun.status,
         card:annual.current(annualData,annualRun),book:annual.portfolio(annualData,annualRun),
         result:annualRun.lastResult,score:annualRun.status==='active'?null:annual.score(annualData,annualRun),
         outcomes:annualRun.index?annual.outcomes(annualData,annualRun):null})
        """
        guard let text = try evaluate(expression).toString(), let bytes = text.data(using: .utf8) else { throw AnnualError.message("The source portfolio could not be decoded.") }
        let snapshot = try JSONDecoder().decode(AnnualSnapshot.self, from: bytes)
        let asOf = try evaluate("annualData.asOf").toString() ?? ""
        runtime.exceptionHandler = nil
        return AnnualBootstrap(context: runtime, snapshot: snapshot, asOf: asOf, restored: restored, warning: warning)
    }
    private func evaluate(_ script: String) throws -> JSValue {
        jsError = nil
        guard let result = context?.evaluateScript(script), jsError == nil else {
            throw AnnualError.message(jsError ?? "The portfolio calculation failed.")
        }
        return result
    }
    private func read<T: Decodable>(_ script: String, as type: T.Type) throws -> T {
        guard let text = try evaluate("JSON.stringify(" + script + ")").toString(), let bytes = text.data(using: .utf8) else {
            throw AnnualError.message("The annual portfolio result could not be read.")
        }
        return try JSONDecoder().decode(type, from: bytes)
    }
    private func updateSnapshot() throws {
        snapshot = try read("""
        {index:annualRun.index,rounds:annualRun.rounds,status:annualRun.status,
         card:annual.current(annualData,annualRun),book:annual.portfolio(annualData,annualRun),
         result:annualRun.lastResult,score:annualRun.status==='active'?null:annual.score(annualData,annualRun),
         outcomes:annualRun.index?annual.outcomes(annualData,annualRun):null}
        """, as: AnnualSnapshot.self)
    }
    func start() {
        guard isReady else { return }
        do {
            _ = try evaluate("annualRun=annual.create(annualData)")
            try updateSnapshot(); draft = [:]; screen = .decision; error = nil
            validateDraft(); try persist(reveal: false)
        } catch { self.error = error.localizedDescription }
    }
    func resume() {
        guard hasSave, let snapshot else { return }
        screen = defaults.bool(forKey: revealKey) && snapshot.result != nil ? .reveal : snapshot.status == "active" ? .decision : .finish
    }
    func menu() { screen = .menu }
    func setWeight(_ value: Double, for id: String) {
        guard value.isFinite, (0...1).contains(value), snapshot?.card?.companies.contains(where: { $0.id == id && $0.canInvest }) == true else { return }
        if value == 0 { draft.removeValue(forKey: id) } else { draft[id] = value }
        validateDraft()
        if let bytes = try? JSONEncoder().encode(draft) { defaults.set(bytes, forKey: draftKey) }
    }
    func clearWeights() { draft = [:]; validateDraft(); defaults.removeObject(forKey: draftKey) }
    func equalWeightUniverse() {
        guard screen == .decision, let card = snapshot?.card else { return }
        let supported = card.companies.filter(\.canInvest)
        guard !supported.isEmpty else { return }
        let weight = 1.0 / Double(supported.count)
        draft = Dictionary(uniqueKeysWithValues: supported.map { ($0.id, weight) })
        validateDraft()
        if let bytes = try? JSONEncoder().encode(draft) { defaults.set(bytes, forKey: draftKey) }
    }
    private func validateDraft() {
        guard snapshot?.status == "active" else { validation = nil; return }
        do {
            context?.setObject(draft, forKeyedSubscript: "annualWeights" as NSString)
            validation = try read("annual.validateAllocation(annualData,annualRun,annualWeights)", as: AnnualValidation.self)
        } catch { self.error = error.localizedDescription }
    }
    func commit() {
        guard screen == .decision, validation?.valid == true else { return }
        do {
            context?.setObject(draft, forKeyedSubscript: "annualWeights" as NSString)
            _ = try evaluate("annualRun=annual.allocate(annualData,annualRun,annualWeights)")
            try updateSnapshot(); screen = .reveal; error = nil; clearWeights()
            try persist(reveal: true)
            if snapshot?.status != "active" { saveScore() }
        } catch { self.error = error.localizedDescription }
    }
    func advance() {
        guard let snapshot else { return }
        screen = snapshot.status == "active" ? .decision : .finish
        defaults.set(false, forKey: revealKey)
        validateDraft()
    }
    func companyHistory(_ id: String) -> AnnualCompanyHistory? {
        do {
            context?.setObject(id, forKeyedSubscript: "annualCompanyID" as NSString)
            return try read("annual.companyHistory(annualData,annualRun,annualCompanyID)", as: AnnualCompanyHistory.self)
        } catch { self.error = error.localizedDescription; return nil }
    }
    private func persist(reveal: Bool) throws {
        guard let wire = try evaluate("annual.serialize(annualRun)").toString() else { return }
        defaults.set(wire, forKey: saveKey); defaults.set(reveal, forKey: revealKey)
        hasSave = true
        if let bytes = try? JSONEncoder().encode(draft) { defaults.set(bytes, forKey: draftKey) }
    }
    private func storedScores() -> [AnnualSavedScore] {
        guard let bytes = defaults.data(forKey: scoresKey), let values = try? JSONDecoder().decode([AnnualSavedScore].self, from: bytes) else { return [] }
        return values
    }
    private func verifyScores(_ candidates: [AnnualSavedScore]? = nil) {
        records = (candidates ?? storedScores()).compactMap { record in
            do {
                context?.setObject(record.replay, forKeyedSubscript: "annualRecord" as NSString)
                let score = try read("annual.score(annualData,annual.restore(annualData,annualRecord))", as: AnnualScore.self)
                return AnnualVerifiedScore(id: score.runId, date: record.date, score: score)
            } catch { return nil }
        }.sorted { $0.score.finalValue > $1.score.finalValue }
    }
    private func saveScore() {
        guard let score = snapshot?.score else { return }
        do {
            guard let replay = try evaluate("annual.serialize(annualRun)").toString() else { return }
            var values = storedScores().filter { $0.id != score.runId }
            values.append(AnnualSavedScore(id: score.runId, edition: score.datasetId, replay: replay, date: Date()))
            verifyScores(values)
            let best = Set(records.prefix(10).map(\.id))
            let priorEditions = values.filter { $0.edition != score.datasetId }.sorted { $0.date > $1.date }.prefix(40)
            values = values.filter { best.contains($0.id) } + priorEditions
            defaults.set(try JSONEncoder().encode(values), forKey: scoresKey)
            verifyScores()
        } catch { self.error = error.localizedDescription }
    }
    var totalWeight: Double { draft.values.reduce(0, +) }
}
