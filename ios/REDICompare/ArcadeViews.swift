import SwiftUI
import UIKit

private enum PlayStyle {
    static let gold = Color(red: 0.79, green: 0.66, blue: 0.46)
    static let green = Color(red: 0.61, green: 0.77, blue: 0.68)
    static func money(_ value: Double) -> String { value.formatted(.currency(code: "USD").precision(.fractionLength(2))) }
    static func percent(_ value: Double) -> String { (value > 0 ? "+" : "") + value.formatted(.percent.precision(.fractionLength(1))) }
    static func year(_ day: String) -> String { String(day.prefix(4)) }
}

@MainActor
struct ArcadeScreen: View {
    @StateObject private var game = ArcadeStore()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var showMethods = false
    @State private var showScores = false
    @State private var pendingMode: String?
    @State private var confirmNew = false
    @AppStorage("hetzerk.play.motionPaused") private var motionPaused = false
    @AppStorage("hetzerk.play.haptics") private var haptics = true

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    if game.screen == .menu { menu }
                    else if game.screen == .decision, let card = game.snapshot?.card { decision(card) }
                    else if game.screen == .reveal, let result = game.snapshot?.result { reveal(result) }
                    else if game.screen == .finish { finish }
                    if let error = game.error {
                        Text(error).font(.footnote).foregroundStyle(HetzerkTheme.yellow)
                            .accessibilityIdentifier("play-error")
                    }
                }
                .frame(maxWidth: 620)
                .padding(.horizontal, 22).padding(.top, 16).padding(.bottom, 24)
                .frame(maxWidth: .infinity)
            }
            .background(HetzerkTheme.ink)
            .foregroundStyle(HetzerkTheme.ivory)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                if game.screen == .decision { allocationDock }
            }
            .toolbarBackground(HetzerkTheme.ink, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { game.menu() } label: {
                        HStack(spacing: 9) { WingHMark(size: 30, animated: false); Text("REDI").font(.system(.headline, design: .serif)); Text("PLAY").font(.system(.caption2, design: .monospaced)).tracking(2) }
                    }.buttonStyle(.plain).accessibilityLabel("REDI Play home").accessibilityIdentifier("play-home")
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button { motionPaused.toggle() } label: { Image(systemName: motionPaused ? "play.circle" : "pause.circle") }
                        .accessibilityLabel(motionPaused ? "Resume decorative motion" : "Pause decorative motion")
                    Button { showScores = true } label: { Image(systemName: "trophy") }
                        .accessibilityLabel("Device leaderboard").accessibilityIdentifier("play-scores")
                    Button { showMethods = true } label: { Image(systemName: "info.circle") }
                        .accessibilityLabel("Game rules and sources")
                }
            }
            .sheet(isPresented: $showMethods) { methods }
            .sheet(isPresented: $showScores) { scores }
            .confirmationDialog("Replace your current run?", isPresented: $confirmNew, titleVisibility: .visible) {
                Button("Start a new run", role: .destructive) { if let pendingMode { game.start(mode: pendingMode) } }
                Button("Keep my run", role: .cancel) { pendingMode = nil }
            } message: { Text("Completed scores stay saved on this device.") }
        }
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.3), value: game.screen)
    }

    private var menu: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack { Eyebrow(text: "A history of conviction"); Spacer(); Text("01 / 12").font(.system(.caption2, design: .monospaced)).foregroundStyle(PlayStyle.gold) }
            Text("Time flies.\nMake it count.")
                .font(.system(size: 47, weight: .regular, design: .serif)).tracking(-2)
                .fixedSize(horizontal: false, vertical: true)
            flight(height: 155, history: [])
            HStack(alignment: .firstTextBaseline) {
                Text("$100").font(.system(size: 43, design: .serif)).foregroundStyle(PlayStyle.gold)
                Text("12 moments. One run.\nHow far can your conviction go?").font(.subheadline).foregroundStyle(HetzerkTheme.muted)
            }
            Button { begin("classic") } label: {
                HStack { VStack(alignment: .leading, spacing: 4) { Text("PLAY CLASSIC").font(.headline); Text("One path through six decades").font(.caption).opacity(0.8) }; Spacer(); Image(systemName: "arrow.right") }
            }.buttonStyle(PlayButtonStyle(primary: true)).disabled(!game.isReady).accessibilityIdentifier("play-classic")
            Button { begin("daily") } label: {
                HStack { VStack(alignment: .leading, spacing: 4) { Text("THE DAILY RUN").font(.headline); Text("A new selection each UTC day").font(.caption).foregroundStyle(HetzerkTheme.muted) }; Spacer(); Image(systemName: "sun.max") }
            }.buttonStyle(PlayButtonStyle()).disabled(!game.isReady).accessibilityIdentifier("play-daily")
            if game.hasSave {
                Button { game.resume() } label: {
                    HStack { Text("Resume your run"); Spacer(); Image(systemName: "arrow.uturn.right") }.font(.subheadline)
                }.buttonStyle(PlayButtonStyle()).accessibilityIdentifier("play-resume")
            }
            Text("Fictional capital. Real historical observations. Each choice rebalances your whole portfolio. No clock, no borrowing, no real-money trades.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted).lineSpacing(3)
            Link("Explore the full Innovation Atlas ↗", destination: URL(string: "https://oftarradiddle.github.io/RED/innovation/")!)
                .font(.footnote).foregroundStyle(PlayStyle.gold)
        }
    }

    private func begin(_ mode: String) {
        if game.hasSave, game.snapshot?.status == "active", (game.snapshot?.round ?? 0) > 0 {
            pendingMode = mode; confirmNew = true
        } else { game.start(mode: mode) }
    }

    private func decision(_ card: PlayCard) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            runHeader(year: PlayStyle.year(card.date), capital: card.capital, round: card.round)
            flight(height: 125, history: game.snapshot?.history ?? [])
            VStack(alignment: .leading, spacing: 15) {
                HStack { Text(card.firm.name.uppercased()).font(.system(.caption2, design: .monospaced)).tracking(1.4); Spacer(); Text(card.firm.ticker).font(.system(.caption, design: .monospaced).weight(.bold)).padding(.horizontal, 9).padding(.vertical, 5).background(HetzerkTheme.red.opacity(0.1), in: Capsule()) }
                Text(card.title).font(.system(size: 30, design: .serif)).tracking(-0.8).fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("play-opportunity")
                Text(card.decision.marketOpportunity ?? "What could this idea become, and what would it cost to get there?")
                    .font(.subheadline).lineSpacing(3)
                HStack(alignment: .top, spacing: 16) {
                    metric("PRICE / ANNUAL EPS", card.decision.valuation?.pe.map { String(format: "%.1f×", $0) } ?? "Not verified")
                    Spacer(minLength: 0)
                    metric("ANNUAL R&D / SALES", card.decision.investment?.rdToSales.map { $0.formatted(.percent.precision(.fractionLength(1))) } ?? "Not verified")
                }.padding(.vertical, 11).overlay(alignment: .top) { Rectangle().fill(HetzerkTheme.ink.opacity(0.12)).frame(height: 1) }
                DisclosureGroup("Read the investment brief") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("THE INVESTMENT").font(.system(.caption2, design: .monospaced).weight(.bold))
                        Text(card.decision.investmentThesis ?? "Product-specific spending is not established.")
                        Text("THE RISK").font(.system(.caption2, design: .monospaced).weight(.bold))
                        Text(card.decision.risks ?? "Adoption, competition and valuation remain uncertain.")
                        if let filing = card.decision.investment?.availableAt {
                            Text("Annual filing available \(filing). R&D is company-wide expense. P/E uses the latest filed annual EPS, not forward or necessarily trailing-twelve-month earnings.").font(.caption)
                        } else {
                            Text("Historical financials are not verified for this date. Current ratios are never substituted.").font(.caption)
                        }
                        if let source = card.decision.valuation?.sourceUrl, let url = URL(string: source), url.scheme == "https" {
                            Link("Read the dated filing ↗", destination: url)
                        }
                        Text("Reconstructed decision brief · execution date \(card.date)").font(.caption2)
                    }.font(.subheadline).padding(.top, 12).lineSpacing(3)
                }.font(.footnote).tint(HetzerkTheme.red)
            }
            .foregroundStyle(HetzerkTheme.ink).padding(23)
            .background(HetzerkTheme.ivory, in: RoundedRectangle(cornerRadius: 25))
            Text("Your last position is sold at this date’s observed close. Choose how much of today’s capital to put into this company; the rest stays in cash.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted)
        }
    }

    private func metric(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 6) { Text(label).font(.system(size: 8, design: .monospaced)).tracking(0.4); Text(value).font(.system(.subheadline, design: .serif)) }
    }

    private var allocationDock: some View {
        VStack(spacing: 10) {
            HStack { Text("MAKE THE CALL").tracking(1.7); Spacer(); Text("Of your current capital") }
                .font(.system(size: 9, design: .monospaced)).foregroundStyle(HetzerkTheme.muted)
            HStack(spacing: 9) {
                choice("PASS", fraction: 0)
                choice("25%", fraction: 0.25)
                choice("50%", fraction: 0.5)
                choice("ALL IN", fraction: 1)
            }
        }
        .padding(.horizontal, 22).padding(.top, 14).padding(.bottom, 14)
        .background(HetzerkTheme.ink.opacity(0.98))
        .overlay(alignment: .top) { Rectangle().fill(PlayStyle.gold.opacity(0.2)).frame(height: 1) }
    }

    private func choice(_ label: String, fraction: Double) -> some View {
        Button {
            if haptics { UIImpactFeedbackGenerator(style: .soft).impactOccurred() }
            game.choose(fraction)
        } label: { Text(label).font(.system(size: 12, weight: .semibold, design: .monospaced)).frame(maxWidth: .infinity).frame(height: 54) }
        .foregroundStyle(fraction == 1 ? HetzerkTheme.ivory : PlayStyle.gold)
        .background(fraction == 1 ? HetzerkTheme.red : HetzerkTheme.raised, in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(PlayStyle.gold.opacity(fraction == 1 ? 0 : 0.25), lineWidth: 1))
        .accessibilityLabel(fraction == 0 ? "Pass and hold cash" : "Invest \(Int(fraction * 100)) percent")
        .accessibilityIdentifier("play-choice-\(Int(fraction * 100))")
    }

    private func reveal(_ result: PlayResult) -> some View {
        VStack(alignment: .leading, spacing: 22) {
            Eyebrow(text: "The years had their say")
            HStack(alignment: .firstTextBaseline) {
                Text(PlayStyle.year(result.from)).foregroundStyle(HetzerkTheme.muted)
                Image(systemName: "arrow.right").font(.title3).foregroundStyle(PlayStyle.gold)
                Text(PlayStyle.year(result.to))
            }.font(.system(size: 44, design: .serif))
            flight(height: 190, history: game.snapshot?.history ?? [])
            Text(PlayStyle.money(result.after)).font(.system(size: 58, design: .serif)).tracking(-2).minimumScaleFactor(0.45).lineLimit(1)
                .contentTransition(.numericText(value: result.after)).accessibilityIdentifier("play-result-capital")
            HStack {
                Image(systemName: result.change >= 0 ? "arrow.up.right" : "arrow.down.right")
                Text(PlayStyle.percent(result.change)).fontWeight(.semibold)
                Text("this round").foregroundStyle(HetzerkTheme.muted)
            }.font(.subheadline).foregroundStyle(result.change >= 0 ? PlayStyle.green : Color(red: 0.94, green: 0.52, blue: 0.45))
            Text(result.allocation == 0 ? "You kept your capital in cash." : "You committed \(Int(result.allocation * 100))% to \(result.company).")
                .font(.title3).fixedSize(horizontal: false, vertical: true)
            Text("\(PlayStyle.money(result.before)) → \(PlayStyle.money(result.after)) · \(result.from) to \(result.to). Whole-company adjusted returns, with remaining cash earning 0%.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted).lineSpacing(3)
            Button { game.advance() } label: {
                HStack { Text(game.snapshot?.status == "active" ? "NEXT OPPORTUNITY" : "SEE YOUR RUN"); Spacer(); Image(systemName: "arrow.right") }.font(.headline)
            }.buttonStyle(PlayButtonStyle(primary: true)).accessibilityIdentifier("play-next")
        }
    }

    private var finish: some View {
        VStack(alignment: .leading, spacing: 22) {
            Eyebrow(text: "Your run / recorded")
            Text("A little capital.\nA long way.").font(.system(size: 43, design: .serif)).tracking(-1.6)
            flight(height: 190, history: game.snapshot?.history ?? [])
            Text(PlayStyle.money(game.snapshot?.book.value ?? 100)).font(.system(size: 55, design: .serif)).tracking(-2).lineLimit(1).minimumScaleFactor(0.45)
                .foregroundStyle(PlayStyle.gold).accessibilityIdentifier("play-finish-capital")
            Text("From $100 · \(game.snapshot?.round ?? 0) decisions · \(game.snapshot?.mode.capitalized ?? "Classic")")
                .font(.subheadline).foregroundStyle(HetzerkTheme.muted)
            Text(game.snapshot?.score?.comparable == true ? "Saved to your device leaderboard. Your score was recalculated from every decision." : "This result is not eligible for the standard board because its final valuation is incomplete.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted)
            Button { game.start(mode: game.snapshot?.mode ?? "classic") } label: {
                HStack { Text("ONE MORE RUN"); Spacer(); Image(systemName: "arrow.clockwise") }.font(.headline)
            }.buttonStyle(PlayButtonStyle(primary: true)).accessibilityIdentifier("play-again")
            HStack {
                Button { showScores = true } label: { Label("Your scores", systemImage: "trophy") }
                Spacer()
                ShareLink(item: game.shareText) { Label("Share result", systemImage: "square.and.arrow.up") }
            }.font(.subheadline).tint(PlayStyle.gold)
            Text("Historical learning, not a forecast. These companies were selected with hindsight; surviving businesses are overrepresented.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted)
        }
    }

    private func runHeader(year: String, capital: Double, round: Int) -> some View {
        VStack(spacing: 13) {
            HStack(alignment: .firstTextBaseline) {
                Text(year).font(.system(size: 40, design: .serif)).foregroundStyle(PlayStyle.gold)
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text("YOUR CAPITAL").font(.system(size: 9, design: .monospaced)).tracking(1.6).foregroundStyle(HetzerkTheme.muted)
                    Text(PlayStyle.money(capital)).font(.system(.title2, design: .serif)).contentTransition(.numericText(value: capital))
                }
            }
            HStack(spacing: 5) {
                ForEach(1...12, id: \.self) { step in Capsule().fill(step <= round ? PlayStyle.gold : HetzerkTheme.raised).frame(height: 3) }
            }
            HStack { Text("\(game.snapshot?.mode.uppercased() ?? "CLASSIC")\(game.snapshot?.day.map { " / " + $0 + " UTC" } ?? " RUN")"); Spacer(); Text("\(round) / 12").accessibilityIdentifier("play-round") }
                .font(.system(size: 9, design: .monospaced)).tracking(1.2).foregroundStyle(HetzerkTheme.muted)
        }
    }

    private func flight(height: CGFloat, history: [PlayHistory]) -> some View {
        PlayFlight(history: history, paused: motionPaused || reduceMotion || scenePhase != .active)
            .frame(height: height)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(history.count > 1 ? "Logarithmic capital path at decision dates, ending \(PlayStyle.money(history.last?.value ?? 100)). Zero, if present, is drawn at the lower bound." : "The Hetzerk wing H in flight")
    }

    private var methods: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    Text("The rules of the run.").font(.system(.largeTitle, design: .serif))
                    Text("Start with $100 of fictional capital. At each of 12 chronological opportunities, the previous position is sold at an observed close. Invest 0%, 25%, 50% or 100% of your current capital in the new company. The remaining cash earns 0%.")
                    Text("The next card marks your investment using the next decision date. The final round ends at the published data cutoff: \(game.asOf). Daily runs use a new, deterministic selection each UTC day; Classic repeats the same selection for this data edition.")
                    Text("The native game works offline. Its bundled rules and dated data match the website edition at release. An app update can introduce a new edition; scores from different editions are not combined.")
                    Text("Yahoo adjusted prices are total-return proxies with provider split and dividend adjustments. There are no fees, taxes, borrowing or actual share purchases. Corporate actions and missing delisted histories can limit completeness. The curated company selection favors survivors. A company’s stock return is not the causal return on one invention.")
                    Text("Dated valuation and R&D figures appear when supported by filings available before the decision. Missing values remain unavailable. The briefs are editorial reconstructions, not original forecasts.")
                    Text("Progress and scores stay on this device. Scores are verified by replay; there is no account, public ranking, real-money wager or prize. Sharing opens Apple’s share sheet and only sends what you choose to send.")
                    Toggle("Haptic feedback", isOn: $haptics)
                    Toggle("Pause decorative motion", isOn: $motionPaused)
                    Link("Sources and complete methodology ↗", destination: URL(string: "https://oftarradiddle.github.io/RED/innovation/#atlas-method")!)
                }.font(.subheadline).lineSpacing(4).padding(24)
            }.background(HetzerkTheme.ink).foregroundStyle(HetzerkTheme.ivory)
                .navigationTitle("How to play").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { showMethods = false } } }
        }.tint(PlayStyle.gold)
    }

    private var scores: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text("Your personal bests.").font(.system(.largeTitle, design: .serif))
                    Text("This device only. The top ten runs per edition are kept, for Classic and the seven most recent Daily editions. Different modes, days and data editions have separate boards.")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                    if game.records.isEmpty {
                        ContentUnavailableView("Your first run awaits", systemImage: "trophy", description: Text("Finish a run to record a verified score."))
                    } else {
                        let groups = Dictionary(grouping: game.records, by: { $0.editionId })
                        ForEach(groups.keys.sorted(), id: \.self) { edition in
                            if let rows = groups[edition], let first = rows.first {
                                VStack(alignment: .leading, spacing: 16) {
                                    Eyebrow(text: first.mode + (first.day.map { " / " + $0 + " UTC" } ?? ""))
                                    ForEach(Array(rows.prefix(10).enumerated()), id: \.element.id) { index, record in
                                        HStack { Text(String(format: "%02d", index + 1)).foregroundStyle(HetzerkTheme.muted); Spacer(); Text(PlayStyle.money(record.value)).font(.system(.title2, design: .serif)); Text(PlayStyle.percent(record.change)).font(.caption).foregroundStyle(PlayStyle.gold) }
                                            .accessibilityIdentifier("play-score-row")
                                    }
                                }.padding(20).background(HetzerkTheme.surface, in: RoundedRectangle(cornerRadius: 22))
                            }
                        }
                    }
                }.padding(24)
            }.background(HetzerkTheme.ink).foregroundStyle(HetzerkTheme.ivory)
                .navigationTitle("Device leaderboard").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { showScores = false } } }
        }.tint(PlayStyle.gold)
    }
}

private struct PlayButtonStyle: ButtonStyle {
    var primary = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.padding(19).frame(maxWidth: .infinity, alignment: .leading)
            .foregroundStyle(primary ? HetzerkTheme.ink : HetzerkTheme.ivory)
            .background(primary ? PlayStyle.gold : HetzerkTheme.raised, in: RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).strokeBorder(.white.opacity(primary ? 0.2 : 0.08), lineWidth: 1))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

private struct PlayFlight: View {
    let history: [PlayHistory]
    var paused: Bool
    private var marks: [Double] { history.map { log10(max($0.value, 0.01)) } }

    var body: some View {
        GeometryReader { geometry in
            TimelineView(.animation(minimumInterval: 1 / 24, paused: paused)) { timeline in
                let time = paused ? 0 : timeline.date.timeIntervalSinceReferenceDate
                ZStack {
                    Canvas { context, size in
                        for row in 0..<4 {
                            var line = Path(); let y = size.height * CGFloat(row + 1) / 5
                            line.move(to: CGPoint(x: 0, y: y)); line.addLine(to: CGPoint(x: size.width, y: y))
                            context.stroke(line, with: .color(PlayStyle.gold.opacity(0.09)), style: StrokeStyle(lineWidth: 1, dash: [3, 8]))
                        }
                        for index in 0..<22 {
                            let phase = Double(index) * 43.7
                            let x = (phase - time * (index % 2 == 0 ? 9 : 5)).truncatingRemainder(dividingBy: size.width)
                            let y = Double(index * 29 % 151) / 151 * size.height
                            let rect = CGRect(x: x < 0 ? x + size.width : x, y: y, width: index % 4 == 0 ? 3 : 1.5, height: 1.5)
                            context.fill(Path(ellipseIn: rect), with: .color(PlayStyle.gold.opacity(0.35)))
                        }
                        if marks.count > 1 {
                            var path = Path()
                            for index in marks.indices {
                                let point = point(index, size: size)
                                if index == 0 { path.move(to: point) } else { path.addLine(to: point) }
                            }
                            context.stroke(path, with: .color(PlayStyle.gold), style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
                        }
                    }
                    let location = marks.count > 1 ? point(marks.count - 1, size: geometry.size) : CGPoint(x: geometry.size.width * 0.5, y: geometry.size.height * 0.5)
                    WingHShape().fill(HetzerkTheme.ivory)
                        .frame(width: 88, height: 88)
                        .rotationEffect(.degrees(paused ? 0 : sin(time * 1.2) * 5))
                        .shadow(color: PlayStyle.gold.opacity(0.28), radius: 20)
                        .position(x: location.x, y: location.y + (paused ? 0 : sin(time * 2) * 6))
                }
            }
        }
        .background(RadialGradient(colors: [HetzerkTheme.red.opacity(0.14), .clear], center: .center, startRadius: 0, endRadius: 220))
        .clipped()
    }

    private func point(_ index: Int, size: CGSize) -> CGPoint {
        let low = (marks.min() ?? 2) - 0.15, high = (marks.max() ?? 2) + 0.15
        return CGPoint(x: 28 + CGFloat(index) / CGFloat(max(marks.count - 1, 1)) * (size.width - 66),
                       y: 32 + CGFloat(1 - (marks[index] - low) / max(high - low, 0.3)) * (size.height - 64))
    }
}
