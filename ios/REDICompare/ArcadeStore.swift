import Foundation
import JavaScriptCore
import SwiftUI

struct PlayHistory: Decodable, Identifiable {
    var date: String
    var value: Double
    var benchmarkValue: Double?
    var id: String { date }
}

struct PlayFirm: Decodable {
    var name: String
    var ticker: String
}

struct PlayValuation: Decodable {
    var pe: Double?
    var fiscalPeriodEnd: String?
    var availableAt: String?
    var sourceUrl: String?
}

struct PlayInvestment: Decodable {
    var rd: Double?
    var rdToSales: Double?
    var fiscalPeriodEnd: String?
    var availableAt: String?
    var sourceUrl: String?
}

struct PlayBrief: Decodable {
    var marketOpportunity: String?
    var investmentThesis: String?
    var risks: String?
    var valuation: PlayValuation?
    var investment: PlayInvestment?
}

struct PlayCard: Decodable {
    var id: String
    var date: String
    var title: String
    var firm: PlayFirm
    var decision: PlayBrief
    var capital: Double
    var round: Int
    var rounds: Int
}

struct PlayBook: Decodable {
    var date: String
    var cash: Double
    var value: Double
    var change: Double
}

struct PlayResult: Decodable {
    var before: Double
    var after: Double
    var change: Double
    var from: String
    var to: String
    var company: String
    var title: String
    var allocation: Double
}

struct PlayScore: Decodable {
    var endValue: Double
    var change: Double
    var mode: String
    var day: String?
    var editionId: String
    var replayId: String
    var complete: Bool
    var comparable: Bool
}

struct PlaySnapshot: Decodable {
    var mode: String
    var day: String?
    var round: Int
    var rounds: Int
    var status: String
    var card: PlayCard?
    var book: PlayBook
    var result: PlayResult?
    var history: [PlayHistory]
    var score: PlayScore?
}

struct PlayRecord: Codable, Identifiable {
    var id: String
    var replay: String
    var date: Date
}

struct VerifiedPlayRecord: Identifiable {
    var id: String
    var value: Double
    var change: Double
    var mode: String
    var day: String?
    var editionId: String
    var date: Date
}

/// The native UI runs the same bundled accounting rules as the website. Only
/// canonical decisions are persisted; displayed balances are always replayed.
@MainActor
final class ArcadeStore: ObservableObject {
    enum Screen: Equatable { case menu, decision, reveal, finish }
    @Published var snapshot: PlaySnapshot?
    @Published var screen: Screen = .menu
    @Published var error: String?
    @Published var isReady = false
    @Published var hasSave = false
    @Published var records: [VerifiedPlayRecord] = []
    @Published var asOf = ""

    private var context: JSContext?
    private var jsError: String?
    private let defaults: UserDefaults
    private let saveKey = "hetzerk.play.replay.v1"
    private let revealKey = "hetzerk.play.reveal.v1"
    private let scoresKey = "hetzerk.play.scores.v1"

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--ui-testing") {
            defaults = UserDefaults(suiteName: "com.hetzerk.play.UITests")!
            defaults.removePersistentDomain(forName: "com.hetzerk.play.UITests")
        } else { defaults = .standard }
        #else
        defaults = .standard
        #endif
        do {
            guard let runtime = JSContext() else { throw PlayError.message("The game engine could not start.") }
            context = runtime
            runtime.exceptionHandler = { [weak self] _, value in self?.jsError = value?.toString() }
            for name in ["innovation-game-engine", "innovation-arcade-engine"] {
                guard let url = Bundle.main.url(forResource: name, withExtension: "js") else {
                    throw PlayError.message("A bundled game resource is missing.")
                }
                _ = try evaluate(String(contentsOf: url, encoding: .utf8))
            }
            guard let url = Bundle.main.url(forResource: "dataset", withExtension: "json") else {
                throw PlayError.message("The historical game data is missing.")
            }
            runtime.setObject(try String(contentsOf: url, encoding: .utf8), forKeyedSubscript: "archiveText" as NSString)
            _ = try evaluate("var archive = JSON.parse(archiveText); var run = null; var arcade = InnovationArcade;")
            asOf = try evaluate("archive.asOf").toString() ?? ""
            isReady = true
            if let saved = defaults.string(forKey: saveKey) {
                runtime.setObject(saved, forKeyedSubscript: "savedReplay" as NSString)
                do {
                    _ = try evaluate("run = arcade.restore(archive, savedReplay)")
                    try updateSnapshot()
                    hasSave = true
                } catch {
                    self.error = "Your saved run belongs to another data edition. Start a fresh run to play this edition."
                }
            }
            verifyRecords()
        } catch { self.error = error.localizedDescription }
    }

    private enum PlayError: LocalizedError {
        case message(String)
        var errorDescription: String? { if case .message(let value) = self { return value }; return nil }
    }

    private func evaluate(_ script: String) throws -> JSValue {
        jsError = nil
        guard let value = context?.evaluateScript(script), jsError == nil else {
            throw PlayError.message(jsError ?? "The game could not complete this action.")
        }
        return value
    }

    private func updateSnapshot() throws {
        let expression = """
        JSON.stringify({mode:run.mode,day:run.day,round:run.round,rounds:run.rounds,status:run.status,
          card:arcade.current(archive,run),book:arcade.portfolio(archive,run),result:run.lastResult,
          history:run.state.history,score:run.status==='active'?null:arcade.score(archive,run)})
        """
        guard let text = try evaluate(expression).toString(), let bytes = text.data(using: .utf8) else {
            throw PlayError.message("The game state could not be read.")
        }
        snapshot = try JSONDecoder().decode(PlaySnapshot.self, from: bytes)
    }

    func start(mode: String) {
        guard isReady, mode == "classic" || mode == "daily" else { return }
        do {
            context?.setObject(mode, forKeyedSubscript: "selectedMode" as NSString)
            context?.setObject(Self.utcDay, forKeyedSubscript: "selectedDay" as NSString)
            _ = try evaluate("run = arcade.create(archive,{mode:selectedMode,day:selectedMode==='daily'?selectedDay:undefined})")
            try updateSnapshot()
            screen = .decision
            error = nil
            try persist(reveal: false)
        } catch { self.error = error.localizedDescription }
    }

    func resume() {
        guard hasSave, let snapshot else { return }
        if defaults.bool(forKey: revealKey), snapshot.result != nil { screen = .reveal }
        else { screen = snapshot.status == "active" ? .decision : .finish }
    }

    func choose(_ fraction: Double) {
        guard screen == .decision else { return }
        do {
            context?.setObject(fraction, forKeyedSubscript: "chosenFraction" as NSString)
            _ = try evaluate("run = arcade.choose(archive, run, chosenFraction)")
            try updateSnapshot()
            screen = .reveal
            error = nil
            try persist(reveal: true)
            if snapshot?.status != "active" { saveScore() }
        } catch { self.error = error.localizedDescription }
    }

    func advance() {
        guard let snapshot else { return }
        screen = snapshot.status == "active" ? .decision : .finish
        defaults.set(false, forKey: revealKey)
        if screen == .finish { saveScore() }
    }

    func menu() { screen = .menu }

    private func persist(reveal: Bool) throws {
        guard let text = try evaluate("arcade.serialize(run)").toString() else { return }
        defaults.set(text, forKey: saveKey)
        defaults.set(reveal, forKey: revealKey)
        hasSave = true
    }

    private func saveScore() {
        guard let score = snapshot?.score, score.complete, score.comparable else { return }
        do {
            guard let replay = try evaluate("arcade.serialize(run)").toString() else { return }
            var stored = savedRecords()
            let identifier = score.editionId + ":" + score.replayId
            stored.removeAll { $0.id == identifier }
            stored.insert(PlayRecord(id: identifier, replay: replay, date: Date()), at: 0)
            verifyRecords(stored)
            let groups = Dictionary(grouping: records, by: { $0.editionId })
            let editions = groups.keys.sorted { a, b in
                let left = groups[a]!, right = groups[b]!
                if (left.first?.mode == "classic") != (right.first?.mode == "classic") { return left.first?.mode == "classic" }
                return (left.map(\.date).max() ?? .distantPast) > (right.map(\.date).max() ?? .distantPast)
            }
            let retainedEditions = Array(editions.filter { groups[$0]?.first?.mode == "classic" }.prefix(1)) + Array(editions.filter { groups[$0]?.first?.mode != "classic" }.prefix(7))
            let retained = Set(retainedEditions.flatMap { edition in
                (groups[edition] ?? []).sorted { $0.value > $1.value }.prefix(10).map(\.id)
            })
            defaults.set(try JSONEncoder().encode(stored.filter { retained.contains($0.id) }), forKey: scoresKey)
            verifyRecords()
        } catch { self.error = error.localizedDescription }
    }

    private func savedRecords() -> [PlayRecord] {
        guard let bytes = defaults.data(forKey: scoresKey), let stored = try? JSONDecoder().decode([PlayRecord].self, from: bytes) else { return [] }
        return stored
    }

    private func verifyRecords(_ candidates: [PlayRecord]? = nil) {
        records = (candidates ?? savedRecords()).compactMap { record in
            do {
                context?.setObject(record.replay, forKeyedSubscript: "scoreReplay" as NSString)
                guard let text = try evaluate("JSON.stringify(arcade.score(archive, arcade.restore(archive, scoreReplay)))").toString(),
                      let bytes = text.data(using: .utf8) else { return nil }
                let score = try JSONDecoder().decode(PlayScore.self, from: bytes)
                guard score.complete, score.comparable else { return nil }
                return VerifiedPlayRecord(id: record.id, value: score.endValue, change: score.change,
                                          mode: score.mode, day: score.day, editionId: score.editionId, date: record.date)
            } catch { return nil }
        }.sorted { $0.value > $1.value }
    }

    var shareText: String {
        guard let score = snapshot?.score else { return "REDI Play — a history of conviction. https://oftarradiddle.github.io/RED/play/" }
        let dollars = score.endValue.formatted(.currency(code: "USD"))
        return "My fictional $100 became \(dollars) in REDI Play. \(score.mode.capitalized)\(score.day.map { " · " + $0 + " UTC" } ?? "") · \(snapshot?.round ?? 0) historical decisions. Historical learning game; not a forecast. https://oftarradiddle.github.io/RED/play/"
    }

    static var utcDay: String {
        let formatter = ISO8601DateFormatter()
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.formatOptions = [.withFullDate]
        return formatter.string(from: Date())
    }
}
