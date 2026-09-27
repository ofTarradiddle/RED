import SwiftUI
import Charts
import REDICore

private enum Display {
    static let inputDate: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
    static let outputDate: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = .autoupdatingCurrent
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateStyle = .medium
        return formatter
    }()
    static func date(_ value: String) -> Date {
        inputDate.date(from: String(value.prefix(10))) ?? .distantPast
    }
    static func day(_ value: String?) -> String {
        guard let value, date(value) != .distantPast else { return "Not yet available" }
        return outputDate.string(from: date(value))
    }
    static func percent(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "—" }
        return value.formatted(.percent.precision(.fractionLength(2)))
    }
    static func number(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "—" }
        return value.formatted(.number.precision(.fractionLength(2)))
    }
    static func money(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "—" }
        return value.formatted(.currency(code: "USD").precision(.fractionLength(2)))
    }
}

struct ContentView: View {
    @EnvironmentObject private var store: ComparisonStore
    @State private var selectedTab = ProcessInfo.processInfo.arguments.contains("--ui-testing") ? "compare" : "play"
    @AppStorage("hetzerk.native.developmentNoticeDismissed") private var noticeDismissed = false

    var body: some View {
        TabView(selection: $selectedTab) {
            ArcadeScreen()
                .tabItem { Label("Play", systemImage: "gamecontroller") }
                .tag("play")
                .accessibilityIdentifier("app-tab-play")
            CompareScreen()
                .tabItem { Label("Compare", systemImage: "chart.xyaxis.line") }
                .accessibilityIdentifier("app-tab-compare")
                .tag("compare")
            RiskScreen()
                .tabItem { Label("Risk", systemImage: "waveform.path") }
                .accessibilityIdentifier("app-tab-risk")
                .tag("risk")
            FundScreen()
                .tabItem { Label("REDI", systemImage: "square.stack.3d.up") }
                .accessibilityIdentifier("app-tab-fund")
                .tag("fund")
        }
        .tint(HetzerkTheme.ivory)
        .preferredColorScheme(.dark)
        .safeAreaInset(edge: .top, spacing: 0) {
            if !noticeDismissed {
                DevelopmentNotice { noticeDismissed = true }
            }
        }
    }
}

private struct DevelopmentNotice: View {
    let dismiss: () -> Void
    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            Text("開発中")
                .font(.system(.caption, design: .serif).weight(.bold))
                .padding(6)
                .overlay(Rectangle().stroke(HetzerkTheme.ink.opacity(0.65), lineWidth: 1))
                .accessibilityLabel("In development")
            Text("Just for fun and development practice.")
                .font(.footnote.weight(.medium))
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
            Button(action: dismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 14, weight: .semibold))
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Dismiss development notice")
            .accessibilityIdentifier("development-close")
        }
        .foregroundStyle(HetzerkTheme.ink)
        .padding(.leading, 16)
        .padding(.trailing, 3)
        .padding(.vertical, 5)
        .frame(maxWidth: .infinity)
        .background(HetzerkTheme.yellow)
    }
}

private struct AppScreen<Content: View>: View {
    @EnvironmentObject private var store: ComparisonStore
    @State private var showingMethods = false
    @State private var showingSaved = false
    @ViewBuilder var content: Content

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    content
                    Text("Investing involves risk, including possible loss of principal. Past performance does not predict future results.")
                        .font(.caption)
                        .foregroundStyle(HetzerkTheme.muted)
                        .padding(.vertical, 8)
                }
                .frame(maxWidth: 760)
                .padding(.horizontal, 20)
                .padding(.bottom, 24)
                .frame(maxWidth: .infinity)
            }
            .background(HetzerkTheme.ink)
            .foregroundStyle(HetzerkTheme.ivory)
            .refreshable { await store.refresh() }
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(HetzerkTheme.ink, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    HStack(spacing: 9) {
                        WingHMark(size: 32)
                        Text("REDI").font(.system(.headline, design: .serif))
                    }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("Hetzerk REDI Compare")
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button { Task { await store.refresh() } } label: {
                        if store.isLoading { ProgressView().tint(HetzerkTheme.ivory) }
                        else { Image(systemName: "arrow.clockwise") }
                    }
                    .disabled(store.isLoading)
                    .accessibilityLabel("Refresh market data")
                    .accessibilityIdentifier("refresh-button")
                    Button { showingSaved = true } label: { Image(systemName: "bookmark") }
                        .accessibilityLabel("Saved comparisons")
                        .accessibilityIdentifier("saved-button")
                    Button { showingMethods = true } label: { Image(systemName: "info.circle") }
                        .accessibilityLabel("Methods and sources")
                }
            }
            .sheet(isPresented: $showingMethods) { MethodsView() }
            .sheet(isPresented: $showingSaved) { SavedComparisonsView() }
        }
    }
}

private struct PublicationStatus: View {
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let snapshot = store.snapshot {
                Label {
                    Text("Dataset published \(Display.day(snapshot.generatedAt))")
                } icon: {
                    Image(systemName: store.isUsingCache ? "internaldrive" : "clock")
                }
                .font(.caption)
                .foregroundStyle(HetzerkTheme.muted)
                if store.isUsingCache {
                    Text("Saved on this device · pull down to check for updates.")
                        .font(.caption)
                        .foregroundStyle(HetzerkTheme.muted)
                }
                ForEach(snapshot.series.filter { (["REDI"] + store.settings.peers).contains($0.id) && $0.status != "ok" }) { series in
                    Label(series.observations.isEmpty
                          ? "\(series.id): source history is unavailable."
                          : "\(series.id): source update failed. Retained history through \(Display.day(series.asOf)).",
                          systemImage: "exclamationmark.triangle")
                        .font(.caption)
                        .foregroundStyle(HetzerkTheme.yellow)
                        .fixedSize(horizontal: false, vertical: true)
                }
                if snapshot.series.contains(where: { $0.id == "REDI" && $0.isIllustrative }) {
                    Label("REDI is illustrative. Live fund performance will begin at inception.", systemImage: "exclamationmark.circle")
                        .font(.caption)
                        .foregroundStyle(HetzerkTheme.ivory)
                        .padding(13)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(HetzerkTheme.red.opacity(0.22), in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(HetzerkTheme.red.opacity(0.7)))
                }
            }
            if let message = store.errorMessage {
                Label(message, systemImage: "wifi.exclamationmark")
                    .font(.caption)
                    .foregroundStyle(HetzerkTheme.yellow)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityIdentifier("publication-status")
    }
}

private struct CompareScreen: View {
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        AppScreen {
            PageHeading(eyebrow: "01 / A common starting point", title: "Perspective,\nin your pocket.",
                        subtitle: "Put REDI beside the market. Follow the differences.")
            PublicationStatus()
            ResearchEntryCard(placement: "compare")
            ComparisonControls()
            if let result = store.result, !result.series.isEmpty {
                ComparisonChartCard(result: result)
                ComparisonResults(result: result)
                ResultWarnings(result: result)
                ShareLink(item: store.shareSummary) {
                    Label("Share this comparison", systemImage: "square.and.arrow.up")
                        .font(.subheadline.weight(.medium))
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
            } else {
                EmptyDataCard()
                if let result = store.result { ResultWarnings(result: result) }
            }
        }
    }
}

private struct ComparisonControls: View {
    @EnvironmentObject private var store: ComparisonStore
    private let peers = ["SPY", "VOO", "QQQ", "ITAN", "SYLD"]
    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 19) {
                HStack {
                    Eyebrow(text: "REDI + your reference points")
                    Spacer(minLength: 0)
                }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 72), spacing: 8)], spacing: 8) {
                    ForEach(peers, id: \.self) { symbol in PeerButton(symbol: symbol) }
                }
                Text("Choose up to three ETFs.")
                    .font(.caption)
                    .foregroundStyle(HetzerkTheme.muted)
                VStack(alignment: .leading, spacing: 8) {
                    Text("REDI valuation").font(.caption).foregroundStyle(HetzerkTheme.muted)
                    Picker("REDI valuation", selection: Binding(
                        get: { store.settings.basis },
                        set: { value in store.updateSettings { $0.basis = value } }
                    )) {
                        ForEach(REDIBasis.allCases) { basis in Text(basis.title).tag(basis) }
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("basis-picker")
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("Calculation").font(.caption).foregroundStyle(HetzerkTheme.muted)
                    Picker("Calculation", selection: Binding(
                        get: { store.settings.returnMode },
                        set: { value in store.updateSettings { $0.returnMode = value } }
                    )) {
                        ForEach(ReturnMode.allCases) { mode in Text(mode.title).tag(mode) }
                    }
                    .pickerStyle(.menu)
                    .tint(HetzerkTheme.ivory)
                    .labelsHidden()
                    .accessibilityIdentifier("mode-picker")
                }
                Divider().overlay(HetzerkTheme.ivory.opacity(0.08))
                PeriodSelector()
            }
        }
    }
}

private struct PeerButton: View {
    @EnvironmentObject private var store: ComparisonStore
    let symbol: String
    private var selected: Bool { store.settings.peers.contains(symbol) }
    private var limitReached: Bool { !selected && store.settings.peers.count >= 3 }
    var body: some View {
        Button {
            store.updateSettings { settings in
                if settings.peers.contains(symbol) { settings.peers.removeAll { $0 == symbol } }
                else if settings.peers.count < 3 { settings.peers.append(symbol) }
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: selected ? "checkmark" : "plus")
                    .font(.caption2.weight(.bold))
                Text(symbol).font(.system(.caption, design: .monospaced).weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 44)
            .foregroundStyle(selected ? HetzerkTheme.ivory : HetzerkTheme.muted)
            .background(selected ? HetzerkTheme.red : HetzerkTheme.ink.opacity(0.45), in: RoundedRectangle(cornerRadius: 11))
            .overlay(RoundedRectangle(cornerRadius: 11).stroke(HetzerkTheme.ivory.opacity(selected ? 0.15 : 0.07)))
            .opacity(limitReached ? 0.5 : 1)
        }
        .buttonStyle(.plain)
        .disabled(limitReached)
        .accessibilityLabel(symbol)
        .accessibilityValue(selected ? "Selected" : "Not selected")
        .accessibilityHint(limitReached ? "Remove an ETF to choose another." : "Toggle comparison ETF.")
        .accessibilityAddTraits(selected ? .isSelected : [])
        .accessibilityIdentifier("peer-\(symbol)")
    }
}

private struct PeriodSelector: View {
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 4) {
                ForEach(ComparisonPeriod.allCases) { period in
                    Button {
                        store.updateSettings { $0.period = period }
                    } label: {
                        Text(period.title)
                            .font(.system(.caption, design: .monospaced).weight(.semibold))
                            .padding(.horizontal, 10)
                            .frame(minHeight: 44)
                            .foregroundStyle(store.settings.period == period ? HetzerkTheme.ink : HetzerkTheme.muted)
                            .background(store.settings.period == period ? HetzerkTheme.ivory : .clear,
                                        in: RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(period.title) period")
                    .accessibilityAddTraits(store.settings.period == period ? .isSelected : [])
                    .accessibilityIdentifier(period == .oneYear ? "period-1Y" : "period-\(period.title)")
                }
            }
        }
    }
}

private struct ComparisonChartCard: View {
    let result: REDICore.ComparisonResult
    @State private var selectedDate: Date?

    private var selectedDay: String? {
        guard let selectedDate else { return nil }
        return result.dates.min { abs(Display.date($0).timeIntervalSince(selectedDate)) < abs(Display.date($1).timeIntervalSince(selectedDate)) }
    }
    private var chartRange: ClosedRange<Double> {
        let values = result.series.flatMap { $0.points.map(\.value) }.filter(\.isFinite)
        let low = min(values.min() ?? 100, 100)
        let high = max(values.max() ?? 100, 100)
        let cushion = max((high - low) * 0.12, 1)
        return (low - cushion)...(high + cushion)
    }
    private var axisDates: [Date] {
        guard !result.dates.isEmpty else { return [] }
        let indexes = Set([0.2, 0.5, 0.8].map { Int(Double(result.dates.count - 1) * $0) })
        return indexes.sorted().map { Display.date(result.dates[$0]) }
    }
    private var shortWindow: Bool {
        guard let start = result.start, let end = result.end else { return true }
        return Display.date(end).timeIntervalSince(Display.date(start)) < 90 * 86_400
    }

    var body: some View {
        SculptedCard(padding: 17) {
            VStack(alignment: .leading, spacing: 17) {
                Eyebrow(text: "Growth of $100")
                Text(selectedDay.map { Display.day($0) } ?? "\(Display.day(result.start)) – \(Display.day(result.end))")
                    .font(.caption)
                    .foregroundStyle(HetzerkTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
                chart
                    .frame(height: 242)
                    .accessibilityIdentifier("compare-chart")
                Text("Touch and hold the chart to inspect a date.")
                    .font(.caption2)
                    .foregroundStyle(HetzerkTheme.muted)
                VStack(spacing: 10) {
                    ForEach(result.series, id: \.id) { series in
                        HStack {
                            Circle().fill(HetzerkTheme.color(for: series.id)).frame(width: 7, height: 7)
                            Text(series.id).font(.system(.caption, design: .monospaced).weight(.semibold))
                            if series.isIllustrative {
                                Text("Illustrative").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                            }
                            Spacer(minLength: 5)
                            Text(Display.money(value(for: series)))
                                .font(.system(.subheadline, design: .monospaced))
                                .contentTransition(.numericText())
                        }
                        .accessibilityElement(children: .combine)
                    }
                }
            }
        }
        .onChange(of: result.start) { _, _ in selectedDate = nil }
        .onChange(of: result.end) { _, _ in selectedDate = nil }
    }

    private func value(for series: ComparedSeries) -> Double? {
        if let day = selectedDay { return series.points.first(where: { $0.date == day })?.value }
        return series.points.last?.value
    }

    private var chart: some View {
        Chart {
            RuleMark(y: .value("Starting value", 100))
                .foregroundStyle(HetzerkTheme.ivory.opacity(0.2))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 5]))
            ForEach(result.series, id: \.id) { series in
                ForEach(series.points, id: \.date) { point in
                    LineMark(x: .value("Date", Display.date(point.date)), y: .value("Growth of $100", point.value))
                        .foregroundStyle(by: .value("ETF", series.id))
                        .lineStyle(StrokeStyle(lineWidth: series.id == "REDI" ? 2.8 : 1.7))
                        .interpolationMethod(.linear)
                }
            }
            if let day = selectedDay {
                RuleMark(x: .value("Selected date", Display.date(day)))
                    .foregroundStyle(HetzerkTheme.ivory.opacity(0.6))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 3]))
                ForEach(result.series, id: \.id) { series in
                    if let point = series.points.first(where: { $0.date == day }) {
                        PointMark(x: .value("Date", Display.date(day)), y: .value("Value", point.value))
                            .foregroundStyle(HetzerkTheme.color(for: series.id))
                            .symbolSize(35)
                    }
                }
            }
        }
        .chartForegroundStyleScale(domain: result.series.map(\.id), range: result.series.map { HetzerkTheme.color(for: $0.id) })
        .chartLegend(.hidden)
        .chartYScale(domain: chartRange)
        .chartXSelection(value: $selectedDate)
        .chartXAxis {
            AxisMarks(values: axisDates) { value in
                AxisValueLabel {
                    if let date = value.as(Date.self) {
                        Text(shortWindow
                             ? date.formatted(.dateTime.month(.abbreviated).day())
                             : date.formatted(.dateTime.month(.abbreviated).year(.twoDigits)))
                            .fixedSize()
                            .foregroundStyle(HetzerkTheme.muted)
                    }
                }
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) {
                AxisGridLine().foregroundStyle(HetzerkTheme.ivory.opacity(0.06))
                AxisValueLabel().foregroundStyle(HetzerkTheme.muted)
            }
        }
        .accessibilityLabel("Growth of 100 dollars, \(result.series.map(\.id).joined(separator: ", "))")
    }
}

private struct ComparisonResults: View {
    let result: REDICore.ComparisonResult
    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            Eyebrow(text: "Over the shared period")
            ForEach(result.series, id: \.id) { series in
                HStack(alignment: .firstTextBaseline, spacing: 15) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(series.id).font(.headline)
                            .foregroundStyle(HetzerkTheme.color(for: series.id))
                        Text(series.name).font(.caption).foregroundStyle(HetzerkTheme.muted)
                    }
                    Spacer(minLength: 3)
                    Text(Display.percent(series.metrics.change))
                        .font(.system(.title3, design: .serif))
                        .monospacedDigit()
                        .fixedSize()
                }
                .padding(.vertical, 7)
                .accessibilityElement(children: .combine)
                Divider().overlay(HetzerkTheme.ivory.opacity(0.08))
            }
        }
    }
}

private struct ResultWarnings: View {
    let result: REDICore.ComparisonResult
    var body: some View {
        if !result.warnings.isEmpty {
            VStack(alignment: .leading, spacing: 9) {
                ForEach(Array(result.warnings.enumerated()), id: \.offset) { _, message in
                    Label(message, systemImage: "info.circle")
                        .font(.caption)
                        .foregroundStyle(HetzerkTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

private struct EmptyDataCard: View {
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 13) {
                if store.isLoading { ProgressView().tint(HetzerkTheme.ivory) }
                Image(systemName: "chart.xyaxis.line").font(.title).foregroundStyle(HetzerkTheme.muted)
                Text(store.isLoading ? "Gathering perspective." : "A comparison needs shared history.")
                    .font(.system(.title3, design: .serif))
                Text(store.isLoading ? "Loading the latest published snapshot." : "Refresh market data or try another period and peer selection. Missing history is never replaced with invented returns.")
                    .font(.subheadline).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
}

private struct RiskScreen: View {
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        AppScreen {
            PageHeading(eyebrow: "02 / The path matters", title: "Beyond the\nending value.",
                        subtitle: "Read the drawdowns, variability, and relationships behind a return.")
            PublicationStatus()
            PeriodSelector()
            Text("Uses your Compare selections · \(store.settings.basis.title) · \(store.settings.returnMode.title)")
                .font(.caption).foregroundStyle(HetzerkTheme.muted)
            if let result = store.result, !result.series.isEmpty {
                if let reason = result.riskReason {
                    Label(reason, systemImage: "info.circle")
                        .font(.subheadline).foregroundStyle(HetzerkTheme.yellow)
                }
                ForEach(result.series, id: \.id) { series in RiskCard(series: series) }
                ResultWarnings(result: result)
                Text("Volatility is annualized using 252 trading days. Correlation measures daily co-movement with REDI, not the similarity of holdings. Figures use the same shared observation dates.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            } else {
                EmptyDataCard()
                if let result = store.result { ResultWarnings(result: result) }
            }
        }
    }
}

private struct RiskCard: View {
    let series: ComparedSeries
    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text(series.id).font(.system(.title2, design: .serif))
                        .foregroundStyle(HetzerkTheme.color(for: series.id))
                    Spacer()
                    if series.isIllustrative { Text("Illustrative").font(.caption).foregroundStyle(HetzerkTheme.muted) }
                }
                VStack(spacing: 15) {
                    MetricRow(label: "Maximum drawdown", value: Display.percent(series.metrics.drawdown))
                    MetricRow(label: "Annualized volatility", value: Display.percent(series.metrics.volatility))
                    MetricRow(label: "Correlation to REDI", value: Display.number(series.metrics.correlation))
                }
            }
        }
    }
}

private struct MetricRow: View {
    let label: String
    let value: String
    @Environment(\.dynamicTypeSize) private var typeSize
    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline, spacing: 16) {
                Text(label).font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                Spacer(minLength: 5)
                Text(value).font(.system(.headline, design: .monospaced)).fixedSize()
            }
            VStack(alignment: .leading, spacing: 5) {
                Text(label).font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                Text(value).font(.system(.headline, design: .monospaced))
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement(children: .combine)
    }
}

private struct FundScreen: View {
    @EnvironmentObject private var store: ComparisonStore
    private var fund: FundSeries? { store.snapshot?.series.first(where: { $0.id == "REDI" }) }
    private var latest: Observation? { fund?.observations.max(by: { $0.date < $1.date }) }
    private var premium: Double? {
        guard let latest, let nav = latest.nav, nav > 0 else { return nil }
        return latest.marketPrice / nav - 1
    }
    var body: some View {
        AppScreen {
            PageHeading(eyebrow: "03 / Investing in innovation", title: "REDI for\ntomorrow.",
                        subtitle: "Hetzerk Innovation Factor ETF")
            PublicationStatus()
            SculptedCard {
                VStack(alignment: .leading, spacing: 20) {
                    HStack(alignment: .center, spacing: 16) {
                        WingHMark(size: 62)
                        VStack(alignment: .leading, spacing: 5) {
                            Text("REDI").font(.system(.title, design: .serif))
                            Text("Hetzerk Asset Management").font(.caption).foregroundStyle(HetzerkTheme.muted)
                        }
                    }
                    Divider()
                    Text("Snapshot · \(Display.day(latest?.date))")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                    MetricRow(label: "NAV", value: Display.money(latest?.nav))
                    MetricRow(label: "Market Price", value: Display.money(latest?.marketPrice))
                    MetricRow(label: "Premium / Discount", value: Display.percent(premium))
                    MetricRow(label: "Expense ratio", value: Display.percent(store.snapshot?.expenseRatio))
                    Text("The expense ratio is already reflected in reported fund returns; this app does not deduct it a second time.")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                }
            }
            ResearchEntryCard(placement: "fund")
            VStack(alignment: .leading, spacing: 4) {
                FundLink(title: "Explore the ETF", path: "etfs/redi/")
                FundLink(title: "Holdings", path: "etfs/redi/holdings.html")
                FundLink(title: "Fund documents", path: "etfs/redi/#documents")
                FundLink(title: "Research", path: "research/")
            }
            if let fund {
                Text("Source: \(fund.source). As of \(Display.day(fund.asOf)).")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
}

private struct FundLink: View {
    let title: String
    let path: String
    var body: some View {
        Link(destination: URL(string: "https://oftarradiddle.github.io/RED/\(path)")!) {
            HStack {
                Text(title).font(.subheadline)
                Spacer()
                Image(systemName: "arrow.up.right").font(.caption)
            }
            .padding(.vertical, 14)
            .foregroundStyle(HetzerkTheme.ivory)
            .overlay(alignment: .bottom) { Rectangle().fill(HetzerkTheme.ivory.opacity(0.12)).frame(height: 1) }
        }
    }
}

private struct MethodsView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var store: ComparisonStore
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 23) {
                    PageHeading(eyebrow: "The working notes", title: "Methods & sources", subtitle: "A clear view of what the numbers mean.")
                    MethodNote(title: "One starting point", text: "Each series begins at $100 on the first shared observation date within your chosen period. The shared start may be later than the requested date. Missing observations are not forward-filled.")
                    MethodNote(title: "NAV and Market Price", text: "The valuation selector changes REDI only. Peer ETFs use their exchange market prices. NAV is the fund's per-share net asset value; Market Price is the price at which shares trade. These can differ.")
                    MethodNote(title: "Price and distributions", text: "Price change excludes distribution reinvestment. The reinvested calculation assumes cash distributions are reinvested at the ex-date closing price: each daily factor is (closing price + distribution) divided by the previous closing price. The published prices and per-share distributions are already split-adjusted; split ratios and adjusted-close adjustments are not applied a second time. This is a daily historical comparison, not an intraday quote or execution price.")
                    MethodNote(title: "Risk, in context", text: "Maximum drawdown is the largest decline from a previous peak within the selected window. Volatility is the sample standard deviation of daily returns, annualized by the square root of 252. Correlation compares daily returns with REDI. Insufficient or irregular observations can prevent a reliable risk estimate.")
                    MethodNote(title: "Fees and precision", text: "Reported fund prices and NAV already reflect fund-level expenses. We do not subtract the expense ratio again. Investor taxes, brokerage costs, bid–ask spreads, and individual execution prices are not included. Source corrections or rounding may change historical results.")
                    MethodNote(title: "Refresh and offline use", text: "Refresh checks for the latest published daily dataset. It does not request a new market quote. The last successful snapshot is saved on your device for offline use; publication and observation dates remain visible. Weekends, holidays, and provider delays can leave prices unchanged.")
                    MethodNote(title: "Illustrative REDI history", text: "Until the fund's live provider feed is connected, REDI data is illustrative and is not an actual fund performance record. Live comparisons should begin at the fund's inception. Illustrative and live histories must not be spliced into one performance series.")
                    VStack(alignment: .leading, spacing: 14) {
                        Eyebrow(text: "Published sources")
                        if let snapshot = store.snapshot {
                            ForEach(snapshot.series, id: \.id) { series in
                                VStack(alignment: .leading, spacing: 5) {
                                    Text("\(series.id) · \(series.source)").font(.subheadline.weight(.medium))
                                    Text("Observations through \(Display.day(series.asOf))")
                                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                                    if series.status != "ok" {
                                        Text(series.observations.isEmpty ? "Source unavailable" : "Source update failed · retained history")
                                            .font(.caption).foregroundStyle(HetzerkTheme.yellow)
                                    }
                                    if let sourceURL = series.sourceURL, let url = URL(string: sourceURL), ["https", "http"].contains(url.scheme ?? "") {
                                        Link("View source ↗", destination: url).font(.caption)
                                    }
                                }
                            }
                        } else { Text("Load a published snapshot to see its source dates.").font(.subheadline) }
                    }
                    MethodNote(title: "On this device", text: "Your comparison settings, named comparisons, and the last downloaded market snapshot are stored locally. No account is required. Sharing a comparison uses the iOS share sheet, where you choose the destination.")
                    FundLink(title: "Privacy policy", path: "privacy/")
                    Text("For research and development. Not investment advice or an offer to buy or sell securities.")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                }
                .frame(maxWidth: 760, alignment: .leading)
                .padding(22)
                .frame(maxWidth: .infinity)
            }
            .background(HetzerkTheme.ink)
            .foregroundStyle(HetzerkTheme.ivory)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
        .tint(HetzerkTheme.ivory)
        .preferredColorScheme(.dark)
    }
}

private struct MethodNote: View {
    let title: String
    let text: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.system(.title3, design: .serif))
            Text(text).font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct SavedComparisonsView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var store: ComparisonStore
    @State private var name = ""
    private var canSave: Bool { !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    var body: some View {
        NavigationStack {
            List {
                Section {
                    TextField("Name this comparison", text: $name)
                        .textInputAutocapitalization(.sentences)
                        .submitLabel(.done)
                        .accessibilityIdentifier("saved-name")
                        .onSubmit { save() }
                    Text("REDI + \(store.settings.peers.joined(separator: ", ")) · \(store.settings.period.title)")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                    Button("Save current comparison", systemImage: "bookmark.fill") { save() }
                        .disabled(!canSave)
                        .accessibilityIdentifier("save-comparison-button")
                } header: { Text("Keep a perspective") }
                    .listRowBackground(HetzerkTheme.surface)
                Section {
                    if store.savedComparisons.isEmpty {
                        Text("Saved comparisons stay on this device. Their values refresh with the latest published dataset.")
                            .font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                    }
                    ForEach(store.savedComparisons) { item in
                        Button {
                            store.loadComparison(item)
                            dismiss()
                        } label: {
                            VStack(alignment: .leading, spacing: 6) {
                                Text(item.name).font(.headline).foregroundStyle(HetzerkTheme.ivory)
                                Text("REDI + \(item.settings.peers.joined(separator: ", ")) · \(item.settings.period.title)")
                                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
                            }
                            .padding(.vertical, 4)
                        }
                        .accessibilityHint("Load this comparison")
                        .swipeActions {
                            Button("Delete", role: .destructive) { store.removeComparison(id: item.id) }
                        }
                    }
                } header: { Text("Saved comparisons") }
                    .listRowBackground(HetzerkTheme.surface)
            }
            .scrollContentBackground(.hidden)
            .background(HetzerkTheme.ink)
            .navigationTitle("Saved comparisons")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
        .tint(HetzerkTheme.ivory)
        .preferredColorScheme(.dark)
    }

    private func save() {
        guard canSave else { return }
        store.saveComparison(name: name.trimmingCharacters(in: .whitespacesAndNewlines))
        name = ""
    }
}
