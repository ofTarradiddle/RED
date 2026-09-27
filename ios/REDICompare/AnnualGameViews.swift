import SwiftUI
import Charts

private enum AnnualStyle {
    static let gold = Color(red: 0.80, green: 0.67, blue: 0.46)
    static let line = Color(red: 0.86, green: 0.28, blue: 0.27)
    static let green = Color(red: 0.60, green: 0.77, blue: 0.67)
    static let formatter: DateFormatter = {
        let value = DateFormatter(); value.locale = Locale(identifier: "en_US_POSIX")
        value.timeZone = TimeZone(secondsFromGMT: 0); value.dateFormat = "yyyy-MM-dd"; return value
    }()
    static func date(_ day: String) -> Date { formatter.date(from: day) ?? .distantPast }
    static func money(_ value: Double) -> String { value.formatted(.currency(code: "USD").precision(.fractionLength(2))) }
    static func percent(_ value: Double) -> String { value.formatted(.percent.precision(.fractionLength(1))) }
    static func compact(_ value: Double?) -> String {
        guard let value else { return "Not verified" }
        return "$" + value.formatted(.number.notation(.compactName).precision(.fractionLength(1)))
    }
}

@MainActor
struct AnnualGameScreen: View {
    @StateObject private var game = AnnualGameStore()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var search = ""
    @State private var onlySelected = false
    @State private var company: AnnualCompany?
    @State private var ownedHistory: AnnualCompanyHistory?
    @State private var showQuick = false
    @State private var showRules = false
    @State private var showScores = false
    @State private var confirmNew = false
    @State private var allOutcomes = false
    @State private var outcomeSearch = ""
    @FocusState private var searchFocused: Bool

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 22) {
                        Color.clear.frame(height: 0).id("annual-top")
                        if game.screen == .menu { menu }
                        else if game.screen == .decision, let card = game.snapshot?.card { decision(card) }
                        else if game.screen == .reveal, let result = game.snapshot?.result { reveal(result) }
                        else if game.screen == .finish { finish }
                        if let error = game.error {
                            Text(error).font(.footnote).foregroundStyle(HetzerkTheme.yellow).accessibilityIdentifier("annual-error")
                        }
                    }
                    .frame(maxWidth: 760, alignment: .leading).padding(.horizontal, 20).padding(.bottom, 25)
                    .frame(maxWidth: .infinity)
                }
                .onChange(of: game.screen) { _, _ in search = ""; onlySelected = false; proxy.scrollTo("annual-top", anchor: .top) }
            }
            .background(HetzerkTheme.ink).foregroundStyle(HetzerkTheme.ivory)
            .safeAreaInset(edge: .bottom, spacing: 0) { if game.screen == .decision { allocationDock } }
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(HetzerkTheme.ink, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { game.menu() } label: {
                        HStack(spacing: 9) { WingHMark(size: 30, animated: false); Text("REDI PLAY").font(.system(.caption, design: .monospaced)).tracking(1.5) }
                    }.buttonStyle(.plain).accessibilityLabel("Annual portfolio home").accessibilityIdentifier("annual-home")
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button { showScores = true } label: { Image(systemName: "trophy") }.accessibilityIdentifier("annual-scores")
                        .accessibilityLabel("Annual device scores")
                    Button { showRules = true } label: { Image(systemName: "info.circle") }.accessibilityLabel("Annual portfolio rules")
                }
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer(); Button("Done") { searchFocused = false }
                }
            }
            .sheet(item: $company) { item in AnnualCompanySheet(company: item, game: game) }
            .sheet(item: $ownedHistory) { history in AnnualOwnedHistorySheet(history: history) }
            .sheet(isPresented: $showRules) { rules }
            .sheet(isPresented: $showScores) { scores }
            .sheet(isPresented: $showQuick) {
                VStack(spacing: 0) {
                    HStack { Text("Quick arcade archive").font(.caption); Spacer(); Button("Done") { showQuick = false } }
                        .padding(.horizontal, 20).padding(.vertical, 12).background(HetzerkTheme.ink)
                    ArcadeScreen()
                }
            }
            .confirmationDialog("Start a new annual portfolio?", isPresented: $confirmNew, titleVisibility: .visible) {
                Button("Start over", role: .destructive) { game.start() }
                Button("Keep my portfolio", role: .cancel) { }
            } message: { Text("This replaces your current progress. Completed device scores remain saved.") }
        }
        .tint(HetzerkTheme.ivory)
    }

    private var menu: some View {
        VStack(alignment: .leading, spacing: 24) {
            Eyebrow(text: "A portfolio. A point of view.")
            HStack(alignment: .top) {
                Text("The long\ngame.").font(.system(size: 57, weight: .regular, design: .serif)).tracking(-2)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(); WingHMark(size: 78).padding(.top, 18)
            }
            Text("Begin at year-end 2010. Read what was filed. Build the entire portfolio. Let a year answer.")
                .font(.title3).foregroundStyle(HetzerkTheme.muted).lineSpacing(4)
            SculptedCard {
                HStack(alignment: .firstTextBaseline) {
                    Text("$100").font(.system(size: 42, design: .serif)).foregroundStyle(AnnualStyle.gold)
                    Spacer()
                    VStack(alignment: .trailing, spacing: 7) {
                        Text("One capital pool").font(.subheadline)
                        Text("Up to 100% invested · Cash earns 0%").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                    }
                }
            }
            AnnualAction(title: "BUILD YOUR PORTFOLIO", symbol: "arrow.right", identifier: "annual-start") {
                if game.hasSave && ((game.snapshot?.index ?? 0) > 0 || !game.draft.isEmpty) { confirmNew = true } else { game.start() }
            }.disabled(!game.isReady)
            if game.isLoading { ProgressView("Opening the historical universe…").font(.caption).accessibilityIdentifier("annual-loading") }
            if game.hasSave {
                Button { game.resume() } label: { Label("Resume your annual portfolio", systemImage: "arrow.uturn.right").frame(maxWidth: .infinity, minHeight: 46) }
                    .buttonStyle(.bordered).accessibilityIdentifier("annual-resume")
            }
            Text("Historical S&P 500 constituent reconstruction. Every name remains visible; unsupported return histories are clearly marked. Monthly observations through \(game.asOf.isEmpty ? "the published source date" : game.asOf).")
                .font(.caption).foregroundStyle(HetzerkTheme.muted).lineSpacing(3)
            Text("Fictional capital. No real-money trades. Past outcomes and available-data selection are not a test of future investing skill.")
                .font(.caption).foregroundStyle(HetzerkTheme.muted)
            Button { showQuick = true } label: { Label("Open the twelve-decision arcade", systemImage: "gamecontroller").font(.footnote) }
                .foregroundStyle(HetzerkTheme.muted).padding(.top, 6).accessibilityIdentifier("annual-quick")
        }.padding(.top, 14)
    }

    private func decision(_ card: AnnualCard) -> some View {
        LazyVStack(alignment: .leading, spacing: 19) {
            HStack { Eyebrow(text: "Year-end \(card.year)"); Spacer(); Text("\(card.round) / \(card.rounds)").font(.caption.monospaced()).accessibilityIdentifier("annual-round") }
            HStack(alignment: .firstTextBaseline) {
                Text(AnnualStyle.money(card.capital)).font(.system(size: 43, design: .serif)).minimumScaleFactor(0.5).lineLimit(1)
                    .contentTransition(.numericText(value: card.capital)).accessibilityIdentifier("annual-capital")
                Spacer(); Text("Capital to allocate").font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
            Text("Build your conviction.").font(.system(.title, design: .serif))
            Text("Information through \(card.cutoff). Your weights execute at the observed close on \(card.executionDate).")
                .font(.caption).foregroundStyle(HetzerkTheme.muted).accessibilityIdentifier("annual-cutoff")
            VStack(alignment: .leading, spacing: 7) {
                Button {
                    game.equalWeightUniverse(); search = ""; onlySelected = true; searchFocused = false
                } label: {
                    Label("Equal weight universe", systemImage: "square.grid.3x3")
                        .font(.subheadline.weight(.medium)).frame(minHeight: 38)
                }
                .accessibilityIdentifier("annual-equal-universe")
                .disabled(card.coverage.supported == 0)
                Text("Draft 100% across all \(card.coverage.supported) companies with return coverage. Every weight stays editable.")
                    .font(.caption2).foregroundStyle(HetzerkTheme.muted)
            }
            HStack(spacing: 9) {
                Image(systemName: "magnifyingglass").foregroundStyle(HetzerkTheme.muted)
                TextField("Find a company or ticker", text: $search).textInputAutocapitalization(.never)
                    .autocorrectionDisabled().focused($searchFocused).submitLabel(.search).onSubmit { searchFocused = false }
                    .accessibilityIdentifier("annual-search")
                if !search.isEmpty { Button { search = "" } label: { Image(systemName: "xmark.circle.fill") }.accessibilityLabel("Clear company search") }
            }.padding(13).background(HetzerkTheme.surface, in: RoundedRectangle(cornerRadius: 13))
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(card.coverage.eligible) eligible · \(card.coverage.supported) with return coverage")
                    Text("\(game.draft.count) selected").accessibilityIdentifier("annual-selected-count")
                }.font(.caption2).foregroundStyle(HetzerkTheme.muted)
                Spacer()
                Button(onlySelected ? "All names" : "Your \(game.draft.count) names") { onlySelected.toggle() }
                    .font(.caption).accessibilityIdentifier("annual-selected-filter")
            }
            ForEach(filteredCompanies(card)) { item in
                Button { company = item; searchFocused = false } label: { companyRow(item) }
                    .buttonStyle(.plain).accessibilityIdentifier("annual-open-\(item.ticker ?? item.id)")
            }
            if filteredCompanies(card).isEmpty { Text("No companies match this view.").font(.subheadline).foregroundStyle(HetzerkTheme.muted) }
        }
    }
    private func filteredCompanies(_ card: AnnualCard) -> [AnnualCompany] {
        card.companies.filter { item in
            (!onlySelected || game.draft[item.id] != nil) && (search.isEmpty || (item.name + " " + (item.ticker ?? "")).localizedCaseInsensitiveContains(search))
        }.sorted { ($0.ticker ?? $0.name) < ($1.ticker ?? $1.name) }
    }
    private func companyRow(_ item: AnnualCompany) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 6) {
                Text(item.ticker ?? "Security").font(.system(.caption, design: .monospaced).weight(.semibold)).foregroundStyle(AnnualStyle.gold)
                Text(item.name).font(.system(.headline, design: .serif)).multilineTextAlignment(.leading)
                if !item.canInvest { Text("Return history incomplete").font(.caption2).foregroundStyle(HetzerkTheme.yellow) }
                else if let pe = item.financials?.valuation?.pe {
                    Text("Filed-earnings P/E \(pe.formatted(.number.precision(.fractionLength(1))))×").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                } else { Text("Open the dated company record").font(.caption2).foregroundStyle(HetzerkTheme.muted) }
            }
            Spacer(minLength: 0)
            VStack(alignment: .trailing, spacing: 9) {
                Text(AnnualStyle.percent(game.draft[item.id] ?? 0)).font(.system(.headline, design: .monospaced))
                Image(systemName: "arrow.up.right").font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
        .padding(17).foregroundStyle(HetzerkTheme.ivory)
        .background(HetzerkTheme.surface, in: RoundedRectangle(cornerRadius: 17))
        .overlay(RoundedRectangle(cornerRadius: 17).stroke(game.draft[item.id] == nil ? HetzerkTheme.ivory.opacity(0.08) : AnnualStyle.gold.opacity(0.45)))
    }
    private var allocationDock: some View {
        VStack(spacing: 9) {
            HStack {
                Text("INVESTED \(AnnualStyle.percent(game.totalWeight))").accessibilityIdentifier("annual-weight-total")
                Spacer(); Text("CASH \(AnnualStyle.percent(max(0, 1 - game.totalWeight)))")
            }.font(.system(.caption2, design: .monospaced)).foregroundStyle(game.totalWeight > 1.0000000001 ? HetzerkTheme.yellow : HetzerkTheme.muted)
            if let messages = game.validation?.errors, !messages.isEmpty {
                Text(messages.joined(separator: " ")).font(.caption2).foregroundStyle(HetzerkTheme.yellow)
            }
            HStack(spacing: 12) {
                Button("Clear") { game.clearWeights(); onlySelected = false }.font(.caption).frame(minHeight: 44).accessibilityIdentifier("annual-clear")
                AnnualAction(title: game.draft.isEmpty ? "HOLD CASH FOR THE YEAR" : "LOCK THE PORTFOLIO", symbol: "arrow.right", identifier: "annual-commit") { searchFocused = false; game.commit() }
                    .disabled(game.validation?.valid != true)
            }
        }
        .padding(.horizontal, 20).padding(.vertical, 12).background(HetzerkTheme.ink.opacity(0.98))
        .overlay(alignment: .top) { Rectangle().fill(AnnualStyle.gold.opacity(0.22)).frame(height: 1) }
    }

    private func reveal(_ result: AnnualResult) -> some View {
        LazyVStack(alignment: .leading, spacing: 22) {
            Eyebrow(text: "The \(result.year) decision / revealed")
            Text(AnnualStyle.money(result.after)).font(.system(size: 52, design: .serif)).minimumScaleFactor(0.5).lineLimit(1)
                .accessibilityIdentifier("annual-result-capital")
            Text("\(AnnualStyle.percent(result.change)) this period · \(result.from) → \(result.to)")
                .font(.subheadline).foregroundStyle(result.change >= 0 ? AnnualStyle.green : AnnualStyle.line)
            if result.partial { Text("Partial final year through the latest supplied observation.").font(.caption).foregroundStyle(HetzerkTheme.muted) }
            AnnualPortfolioChart(history: result.path, benchmark: game.snapshot?.book.benchmark?.path.filter { $0.date >= result.from && $0.date <= result.to } ?? [], rebaseBenchmarkTo: result.before)
            AnnualAction(title: game.snapshot?.status == "active" ? "BUILD NEXT YEAR’S PORTFOLIO" : "SEE THE FULL RECORD", symbol: "arrow.right", identifier: "annual-next") { game.advance() }
            Picker("Results view", selection: $allOutcomes) {
                Text("Your portfolio").tag(false); Text("The year’s universe").tag(true)
            }.pickerStyle(.segmented).accessibilityIdentifier("annual-outcomes-picker")
            if allOutcomes, let outcomes = game.snapshot?.outcomes {
                TextField("Filter the revealed universe", text: $outcomeSearch).textFieldStyle(.roundedBorder)
                    .focused($searchFocused).submitLabel(.search).onSubmit { searchFocused = false }
                    .accessibilityIdentifier("annual-outcome-search")
                ForEach(outcomes.companies.filter { outcomeSearch.isEmpty || ($0.name + " " + ($0.ticker ?? "")).localizedCaseInsensitiveContains(outcomeSearch) }.sorted { ($0.ticker ?? $0.name) < ($1.ticker ?? $1.name) }) { item in
                    Button { openHistory(item.id) } label: {
                        HStack { VStack(alignment: .leading, spacing: 4) { Text(item.ticker ?? item.name).font(.subheadline.weight(.medium)); Text(item.name).font(.caption).foregroundStyle(HetzerkTheme.muted) }; Spacer(); Text(item.periodReturn.map(AnnualStyle.percent) ?? "Unavailable").font(.caption.monospaced()); Image(systemName: "arrow.up.right").font(.caption2) }
                            .padding(.vertical, 10)
                            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                            .contentShape(Rectangle())
                    }.buttonStyle(.plain).accessibilityIdentifier("annual-outcome-\(item.ticker ?? item.id)")
                }
            } else {
                if result.companies.isEmpty { Text("The portfolio stayed in cash. Explore the year’s universe to inspect verified firm returns.").font(.subheadline).foregroundStyle(HetzerkTheme.muted) }
                ForEach(result.companies.sorted { $0.profit > $1.profit }) { item in
                    Button { openHistory(item.id) } label: {
                        SculptedCard(padding: 17) {
                            VStack(alignment: .leading, spacing: 11) {
                                HStack { Text(item.ticker ?? item.name).font(.headline); Spacer(); Text(AnnualStyle.percent(item.weight)).font(.caption.monospaced()) }
                                Text(item.name).font(.caption).foregroundStyle(HetzerkTheme.muted)
                                HStack {
                                    smallMetric("Firm return", AnnualStyle.percent(item.periodReturn))
                                    smallMetric("Your profit", AnnualStyle.money(item.profit))
                                    smallMetric("Contribution", String(format: "%.2f pp", item.contribution * 100))
                                }
                                Text("Inspect your invested periods ↗").font(.caption2).foregroundStyle(AnnualStyle.gold)
                            }
                        }
                    }.buttonStyle(.plain).accessibilityIdentifier("annual-history-\(item.ticker ?? item.id)")
                }
                Text("Contributions are each firm’s profit divided by starting portfolio capital. They add to the portfolio’s period return. Remaining cash earns 0%.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
    private var finish: some View {
        VStack(alignment: .leading, spacing: 22) {
            Eyebrow(text: "Your annual portfolio / complete")
            Text("The record\nis yours.").font(.system(size: 45, design: .serif))
            if let book = game.snapshot?.book {
                Text(AnnualStyle.money(book.value)).font(.system(size: 53, design: .serif)).minimumScaleFactor(0.5).lineLimit(1).accessibilityIdentifier("annual-final-capital")
                Text("From $100 · \(AnnualStyle.percent(book.change)) · Through \(book.date)").font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                AnnualPortfolioChart(history: book.history, benchmark: book.benchmark?.path ?? [], rebaseBenchmarkTo: nil)
                ForEach(book.companies.sorted { $0.profit > $1.profit }) { item in
                    Button { openHistory(item.id) } label: {
                        HStack { VStack(alignment: .leading, spacing: 5) { Text(item.ticker ?? item.name).font(.headline); Text("\(item.periods) invested periods").font(.caption).foregroundStyle(HetzerkTheme.muted) }; Spacer(); VStack(alignment: .trailing, spacing: 5) { Text(AnnualStyle.money(item.profit)).font(.headline.monospaced()); Text(String(format: "%.2f pp of lifetime return", item.contribution * 100)).font(.caption2).foregroundStyle(HetzerkTheme.muted) } }.padding(.vertical, 11)
                    }.buttonStyle(.plain)
                }
                Text("Firm profits include realized and marked gains from periods you owned them. Repeated annual allocations recycle capital; they are not extra external deposits.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
            AnnualAction(title: "START ANOTHER PORTFOLIO", symbol: "arrow.counterclockwise", identifier: "annual-again") { game.start() }
            Button("View verified device scores") { showScores = true }.font(.subheadline)
        }
    }
    private func openHistory(_ id: String) { ownedHistory = game.companyHistory(id) }
    private func smallMetric(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 5) { Text(value).font(.caption.monospaced().weight(.semibold)); Text(label).font(.caption2).foregroundStyle(HetzerkTheme.muted) }.frame(maxWidth: .infinity, alignment: .leading)
    }
    private var rules: some View {
        AnnualSheet(title: "The annual rules") {
            PageHeading(eyebrow: "A record, not a forecast", title: "Read. Allocate.\nLive with it.", subtitle: "Year-end information. First-session execution. One portfolio.")
            Text("Start with $100 at the first observed trading close after the 2010 year-end cutoff. At each rebalance, previous positions are closed at observed return indices. Allocate fractions of the resulting capital across any eligible names, up to 100% in total. Unallocated capital earns 0%.")
            Text("The universe is a public historical S&P 500 constituent reconstruction, not an official licensed index record. Historical identity notes remain visible. All constituents stay listed, including those with missing, delisted or ambiguous return histories. An incomplete selected path blocks calculation; no price is carried forward and no bankruptcy or merger payoff is invented.")
            Text("Only filings and facts dated on or before the decision cutoff appear in company records. Missing earnings ratios or spending figures remain unverified. Company-wide R&D, capital expenditure and acquisition amounts can overlap in accounting; they are not summed into a synthetic investment budget.")
            Text("The monthly path uses observed month-end sessions and annual execution dates. Provider-adjusted prices include its dividend and split adjustments, so neither is applied again. Fees, taxes, inflation and trading costs are excluded. Drawdowns between displayed observations may be larger.")
            Text("Firm return describes one invested period. Contribution is profit divided by portfolio capital. The owned-period record excludes years when you did not hold the firm. Gross allocations can count reinvested capital more than once and are not external deposits.")
            Text("Progress and device scores are saved locally as allocation choices. The bundled engine replays every balance when a save or score is loaded. Only the current source edition is ranked. There is no public leaderboard, account or real-money order.")
            Link("Open the web portfolio lab ↗", destination: URL(string: "https://oftarradiddle.github.io/RED/play/")!)
        }
    }
    private var scores: some View {
        AnnualSheet(title: "Annual device scores") {
            Text("Verified against this bundled data edition.").font(.caption).foregroundStyle(HetzerkTheme.muted)
            if game.records.isEmpty { Text("Finish an annual portfolio to add your first score.") }
            ForEach(Array(game.records.enumerated()), id: \.element.id) { index, record in
                HStack { Text(String(format: "%02d", index + 1)).font(.caption.monospaced()).foregroundStyle(AnnualStyle.gold); Text(record.date, style: .date).font(.caption); Spacer(); Text(AnnualStyle.money(record.score.finalValue)).font(.headline.monospaced()) }.padding(.vertical, 12)
            }
        }
    }
}

private struct AnnualAction: View {
    var title: String
    var symbol: String
    var identifier: String
    var action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack { Text(title).font(.system(.caption, design: .monospaced).weight(.semibold)).tracking(0.5); Spacer(minLength: 8); Image(systemName: symbol) }
                .padding(.horizontal, 17).frame(minHeight: 51).foregroundStyle(HetzerkTheme.ivory)
                .background(LinearGradient(colors: [Color(red: 0.57, green: 0.09, blue: 0.11), HetzerkTheme.red], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 14))
        }.buttonStyle(.plain).accessibilityIdentifier(identifier)
    }
}

private struct AnnualSheet<Content: View>: View {
    @Environment(\.dismiss) private var dismiss
    var title: String
    @ViewBuilder var content: Content
    var body: some View {
        NavigationStack {
            ScrollView { VStack(alignment: .leading, spacing: 21) { content }.font(.subheadline).lineSpacing(3).frame(maxWidth: 760, alignment: .leading).padding(22).frame(maxWidth: .infinity) }
                .background(HetzerkTheme.ink).foregroundStyle(HetzerkTheme.ivory)
                .navigationTitle(title).navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() }.accessibilityIdentifier("annual-sheet-done") } }
        }.tint(HetzerkTheme.ivory)
    }
}

private struct AnnualCompanySheet: View {
    @Environment(\.dismiss) private var dismiss
    let company: AnnualCompany
    @ObservedObject var game: AnnualGameStore
    @State private var percentText = "0"
    @FocusState private var weightFocused: Bool
    private var weight: Double? { Double(percentText.replacingOccurrences(of: ",", with: ".")).map { $0 / 100 } }
    var body: some View {
        AnnualSheet(title: company.ticker ?? "Company record") {
            PageHeading(eyebrow: "Known by \(game.snapshot?.card?.cutoff ?? "the decision date")", title: company.name, subtitle: company.sector ?? "Historical constituent record")
            if let note = company.identityNote { Text(note).font(.caption).foregroundStyle(HetzerkTheme.muted) }
            if company.canInvest {
                SculptedCard {
                    VStack(alignment: .leading, spacing: 15) {
                        Eyebrow(text: "Your allocation")
                        HStack {
                            TextField("Weight", text: $percentText).keyboardType(.decimalPad).focused($weightFocused)
                                .font(.system(size: 37, design: .serif)).accessibilityIdentifier("annual-weight-input")
                            Text("%").font(.title).foregroundStyle(AnnualStyle.gold)
                        }
                        HStack { ForEach([0, 5, 10, 25, 50, 100], id: \.self) { value in Button("\(value)") { percentText = String(value); weightFocused = false }.font(.caption).frame(maxWidth: .infinity, minHeight: 38).background(HetzerkTheme.ink, in: RoundedRectangle(cornerRadius: 7)) } }
                        AnnualAction(title: "APPLY WEIGHT", symbol: "checkmark", identifier: "annual-weight-apply") {
                            if let weight { game.setWeight(weight, for: company.id); dismiss() }
                        }.disabled(weight == nil || !(0...1).contains(weight ?? -1))
                        Text("Weights across every company must total no more than 100%. The remainder stays in cash.").font(.caption).foregroundStyle(HetzerkTheme.muted)
                    }
                }
            } else {
                Text(company.coverage.reason ?? "This historical member remains visible, but its selected-period return path is incomplete.")
                    .font(.subheadline).foregroundStyle(HetzerkTheme.yellow).accessibilityIdentifier("annual-coverage-reason")
                Text("It cannot be included in a calculated portfolio until a reliable observed return path is established.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
                Text("\(company.coverage.observed) / \(company.coverage.required) marks verified. Missing: \(company.coverage.missingDates.prefix(5).joined(separator: ", "))\(company.coverage.missingDates.count > 5 ? "…" : "")").font(.caption)
            }
            if let financials = company.financials {
                SculptedCard {
                    VStack(alignment: .leading, spacing: 14) {
                        Eyebrow(text: "As-filed evidence")
                        Text("Fiscal period \(financials.fiscalPeriodEnd) · Available \(financials.availableAt)").font(.caption).foregroundStyle(HetzerkTheme.muted)
                        if let pe = financials.valuation?.pe {
                            HStack { Text("Price / filed annual EPS"); Spacer(); Text(pe.formatted(.number.precision(.fractionLength(1))) + "×").font(.headline.monospaced()) }
                            if let note = financials.valuation?.note { Text(note).font(.caption).foregroundStyle(HetzerkTheme.muted) }
                        }
                        metric("Revenue", key: "revenue", financials: financials)
                        metric("R&D expense", key: "rd", financials: financials)
                        metric("Capital expenditure", key: "capex", financials: financials)
                        metric("Acquisitions", key: "acquisitions", financials: financials)
                        metric("Operating cash flow", key: "operatingCashFlow", financials: financials)
                        metric("Net income", key: "netIncome", financials: financials)
                        Text("Company-wide figures. Spending categories can overlap; they are not added together. Missing values are not zero.").font(.caption).foregroundStyle(HetzerkTheme.muted)
                    }
                }
                if financials.filings.isEmpty { Text("Narrative filing excerpts are not verified for this cutoff.").font(.caption).foregroundStyle(HetzerkTheme.muted) }
                ForEach(financials.filings) { filing in
                    SculptedCard {
                        VStack(alignment: .leading, spacing: 13) {
                            Eyebrow(text: "\(filing.form ?? "Filing") / \(filing.filed)")
                            if !filing.focusAreas.isEmpty { Text(filing.focusAreas.joined(separator: " · ")).font(.system(.headline, design: .serif)) }
                            if let note = filing.focusNote { Text(note).font(.caption).foregroundStyle(HetzerkTheme.muted) }
                            ForEach(Array(filing.investmentThemes.enumerated()), id: \.offset) { _, theme in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(theme.label).font(.subheadline.weight(.medium))
                                    if let excerpt = theme.excerpt, !excerpt.isEmpty { Text("“\(excerpt)”").font(.system(.subheadline, design: .serif)) }
                                    if let note = theme.note { Text(note).font(.caption).foregroundStyle(HetzerkTheme.muted) }
                                }
                            }
                            sourceLink("Read the original filing ↗", filing.url)
                        }
                    }
                }
            } else { Text("Historical filed financials and investment themes are not verified for this decision cutoff. Current financial ratios are never substituted.").font(.subheadline).foregroundStyle(HetzerkTheme.muted) }
        }
        .onAppear { percentText = ((game.draft[company.id] ?? 0) * 100).formatted(.number.precision(.fractionLength(0...2)).locale(Locale(identifier: "en_US_POSIX"))) }
    }
    private func metric(_ label: String, key: String, financials: AnnualFinancials) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack { Text(label); Spacer(); Text(AnnualStyle.compact(financials.value(key))).font(.caption.monospaced()) }
            if let source = financials.metricSources[key] {
                Text("Period \(source.periodStart.map { $0 + " → " } ?? "")\(source.fiscalPeriodEnd ?? "unverified")").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                sourceLink("\(source.form ?? "Filing") · Filed \(source.filed ?? "") ↗", source.sourceUrl)
            }
        }
    }
    @ViewBuilder private func sourceLink(_ label: String, _ address: String?) -> some View {
        if let address, let url = URL(string: address), url.scheme == "https" { Link(label, destination: url).font(.caption).foregroundStyle(AnnualStyle.gold) }
    }
}

private struct AnnualPortfolioChart: View {
    let history: [AnnualHistoryPoint]
    let benchmark: [AnnualHistoryPoint]
    let rebaseBenchmarkTo: Double?
    var title = "Observed capital path"
    var primaryLabel = "Portfolio"
    var note = "Observed month-end and execution closes. SPY is an ETF proxy, not the index itself. Missing benchmark history is omitted."
    var identifier = "annual-capital-chart"
    @State private var selectedDate: Date?
    private var marks: [AnnualHistoryPoint] {
        guard let baseline = rebaseBenchmarkTo, let first = benchmark.first, first.value > 0 else { return benchmark }
        return benchmark.map { AnnualHistoryPoint(date: $0.date, value: $0.value / first.value * baseline) }
    }
    private var inspected: AnnualHistoryPoint? {
        guard let selectedDate else { return history.last }
        return history.min { abs(AnnualStyle.date($0.date).timeIntervalSince(selectedDate)) < abs(AnnualStyle.date($1.date).timeIntervalSince(selectedDate)) }
    }
    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack { Eyebrow(text: title); Spacer(); Text(primaryLabel + (marks.isEmpty ? "" : " / SPY")).font(.caption2).foregroundStyle(HetzerkTheme.muted) }
                Chart {
                    ForEach(history) { point in LineMark(x: .value("Date", AnnualStyle.date(point.date)), y: .value("Value", point.value)).foregroundStyle(by: .value("Series", primaryLabel)).lineStyle(StrokeStyle(lineWidth: 2.5)) }
                    ForEach(marks) { point in LineMark(x: .value("Date", AnnualStyle.date(point.date)), y: .value("Capital", point.value)).foregroundStyle(by: .value("Series", "SPY")).lineStyle(StrokeStyle(lineWidth: 1.5, dash: [4, 3])) }
                    if let inspected { RuleMark(x: .value("Inspected", AnnualStyle.date(inspected.date))).foregroundStyle(HetzerkTheme.ivory.opacity(0.22)) }
                }
                .chartForegroundStyleScale(domain: [primaryLabel, "SPY"], range: [AnnualStyle.line, HetzerkTheme.muted])
                .chartLegend(.hidden).chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) }
                .chartXSelection(value: Binding(get: { selectedDate }, set: { if let value = $0 { selectedDate = value } }))
                .frame(height: 205).accessibilityIdentifier(identifier)
                if let inspected { HStack { Text(inspected.date).font(.caption.monospaced()); Spacer(); Text(AnnualStyle.money(inspected.value)).font(.headline.monospaced()) } }
                Text(note).font(.caption2).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
}

private struct AnnualOwnedHistorySheet: View {
    let history: AnnualCompanyHistory
    var body: some View {
        AnnualSheet(title: history.periods.isEmpty ? "Company return record" : "Your invested periods") {
            PageHeading(eyebrow: history.ticker ?? "Company", title: history.name, subtitle: "Completed annual returns and your own invested-period record.")
            if let period = history.mostRecentPeriod {
                Eyebrow(text: "Latest completed eligible period / \(period.year)")
                Text("\(period.from) → \(period.to)").font(.caption.monospaced()).accessibilityIdentifier("annual-company-period")
                if let change = period.periodReturn {
                    HStack { Text("Firm return this period"); Spacer(); Text(AnnualStyle.percent(change)).font(.title2.monospaced()) }
                    AnnualPortfolioChart(history: period.path, benchmark: period.benchmark?.path ?? [], rebaseBenchmarkTo: nil,
                        title: "Growth of $100", primaryLabel: period.ticker ?? "Company",
                        note: "Stock and SPY begin at $100 on the same observed execution close. Only the completed eligible interval is shown. Adjusted return indices already include provider dividend and split adjustments.",
                        identifier: "annual-company-return-chart")
                    if let benchmark = period.benchmark, benchmark.status != "available" {
                        Text(benchmark.reason ?? "Matching SPY observations are unavailable.").font(.caption).foregroundStyle(HetzerkTheme.muted)
                    }
                } else {
                    Text(period.coverage.reason ?? "The observed return path is incomplete for this interval.").font(.subheadline).foregroundStyle(HetzerkTheme.yellow)
                }
            }
            if let linkedReturn = history.ownedReturn {
                Eyebrow(text: "Your owned-period return")
                Text(AnnualStyle.percent(linkedReturn)).font(.system(.largeTitle, design: .serif)).accessibilityIdentifier("annual-owned-linked-return")
                AnnualPortfolioChart(history: history.ownedReturnPath, benchmark: [], rebaseBenchmarkTo: nil,
                    title: "Linked growth of $100", primaryLabel: "Owned periods",
                    note: "Returns compound only through the periods when you held this firm. The line stays flat during gaps. This linked return excludes unowned years and is independent of your position sizes; your actual dollar profit appears below.",
                    identifier: "annual-owned-return-chart")
            } else {
                Text("You did not hold this firm in a completed period. The source return above does not contribute to your portfolio.")
                    .font(.subheadline).foregroundStyle(HetzerkTheme.muted).accessibilityIdentifier("annual-never-owned")
            }
            if let summary = history.summary {
                HStack { Text("Lifetime profit"); Spacer(); Text(AnnualStyle.money(summary.profit)).font(.title2.monospaced()) }
                Text(String(format: "%.2f percentage points of your portfolio’s lifetime return", summary.contribution * 100)).font(.caption).foregroundStyle(HetzerkTheme.muted)
                Chart {
                    ForEach(history.path) { point in LineMark(x: .value("Date", AnnualStyle.date(point.date)), y: .value("Cumulative profit", point.profit)).foregroundStyle(AnnualStyle.line).lineStyle(StrokeStyle(lineWidth: 2.5)) }
                    RuleMark(y: .value("Break even", 0)).foregroundStyle(HetzerkTheme.ivory.opacity(0.18))
                }.frame(height: 200).chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) }
                Text("Cumulative contribution stays unchanged while the firm is not held. This is your profit history, not a buy-and-hold stock-return curve.").font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
            ForEach(history.periods) { period in
                SculptedCard {
                    VStack(alignment: .leading, spacing: 11) {
                        Eyebrow(text: "\(period.year) allocation")
                        Text("\(period.from) → \(period.to)").font(.caption.monospaced())
                        HStack { Text("Capital allocated"); Spacer(); Text(AnnualStyle.money(period.invested)) }
                        HStack { Text("Ending value"); Spacer(); Text(AnnualStyle.money(period.endingValue)) }
                        HStack { Text("Firm return while held"); Spacer(); Text(AnnualStyle.percent(period.periodReturn)) }
                        HStack { Text(period.closed ? "Realized profit" : "Marked profit"); Spacer(); Text(AnnualStyle.money(period.profit)) }
                    }.font(.subheadline)
                }
            }
            if let summary = history.summary {
                Text("Gross annual allocations: \(AnnualStyle.money(summary.totalInvested)). This total includes recycled capital across rebalances; it is not the amount of external capital contributed.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
}
