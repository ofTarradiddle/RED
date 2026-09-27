import SwiftUI
import Charts
import REDICore

/// Available offline, independently of the market-comparison refresh or REDI valuation selector.
struct ResearchEntryCard: View {
    @State private var isPresented = false
    var placement: String

    var body: some View {
        Button { isPresented = true } label: {
            SculptedCard(padding: 17) {
                HStack(spacing: 15) {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                        .font(.title2).foregroundStyle(ResearchDisplay.color("INNOVATION_LEADER"))
                    VStack(alignment: .leading, spacing: 5) {
                        Text("The measure of fire").font(.system(.headline, design: .serif))
                        Text("Explore the strategy research · Monthly history")
                            .font(.caption).foregroundStyle(HetzerkTheme.muted)
                    }
                    Spacer(minLength: 0)
                    Image(systemName: "arrow.up.right").font(.caption)
                }
                .foregroundStyle(HetzerkTheme.ivory)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Explore strategy research")
        .accessibilityIdentifier("research-open-\(placement)")
        .sheet(isPresented: $isPresented) { ResearchView() }
    }
}

private enum ResearchDisplay {
    static let formatter: DateFormatter = {
        let value = DateFormatter()
        value.locale = Locale(identifier: "en_US_POSIX")
        value.timeZone = TimeZone(secondsFromGMT: 0)
        value.dateFormat = "yyyy-MM-dd"
        return value
    }()
    static func date(_ value: String) -> Date { formatter.date(from: value) ?? .distantPast }
    static func percent(_ value: Double?) -> String {
        guard let value, value.isFinite else { return "—" }
        return value.formatted(.percent.precision(.fractionLength(1)))
    }
    static func money(_ value: Double) -> String { value.formatted(.currency(code: "USD").precision(.fractionLength(2))) }
    static func color(_ id: String) -> Color {
        switch id {
        case "INNOVATION_LEADER": return Color(red: 0.79, green: 0.19, blue: 0.20)
        case "LAGGARD": return Color(red: 0.80, green: 0.64, blue: 0.34)
        case "MARKET_BACKTEST": return HetzerkTheme.muted
        case "MARKET_EQUAL_WEIGHT": return Color(red: 0.58, green: 0.72, blue: 0.70)
        case "NON_RD": return Color(red: 0.67, green: 0.57, blue: 0.77)
        default: return HetzerkTheme.color(for: id)
        }
    }
}

private struct ResearchView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var store: ComparisonStore
    @State private var dataset: ResearchDataset?
    @State private var result: ResearchResult?
    @State private var selectedIDs = ResearchEngine.defaultSelection
    @State private var period: ResearchPeriod = .all
    @State private var logarithmic = true
    @State private var selectedDate: Date?
    @State private var errorMessage: String?

    private var availableETFs: [FundSeries] {
        (store.snapshot?.series ?? []).filter {
            ResearchEngine.allowedETFs.contains($0.id) && !$0.isIllustrative && !$0.observations.isEmpty && $0.status != "unavailable"
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    PageHeading(eyebrow: "The research archive", title: "The measure\nof fire.",
                                subtitle: "Innovation Leader, Laggard and the Market Backtest. One common starting point.")
                    Text("Hypothetical strategy research · Not REDI fund performance")
                        .font(.caption.weight(.medium)).foregroundStyle(HetzerkTheme.yellow)
                        .accessibilityIdentifier("research-disclaimer")
                    if let dataset {
                        controls(dataset)
                        if let result, !result.series.isEmpty {
                            ResearchChartCard(result: result, logarithmic: logarithmic, selectedDate: $selectedDate)
                            ResearchResultsCard(result: result)
                            ForEach(result.warnings, id: \.self) { text in
                                Text(text).font(.caption).foregroundStyle(HetzerkTheme.muted)
                            }
                        } else if let result {
                            ForEach(result.warnings, id: \.self) { text in
                                Text(text).font(.subheadline).foregroundStyle(HetzerkTheme.muted)
                            }
                        }
                        sourceNotes(dataset)
                    }
                    if let errorMessage { Text(errorMessage).foregroundStyle(HetzerkTheme.yellow) }
                }
                .frame(maxWidth: 760, alignment: .leading)
                .padding(20).frame(maxWidth: .infinity)
            }
            .background(HetzerkTheme.ink).foregroundStyle(HetzerkTheme.ivory)
            .navigationTitle("Strategy research").navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(HetzerkTheme.ink, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }.accessibilityIdentifier("research-done")
                }
            }
        }
        .tint(HetzerkTheme.ivory)
        .task { load() }
        .onChange(of: selectedIDs) { _, _ in recalculate() }
        .onChange(of: period) { _, _ in recalculate() }
        .onChange(of: store.snapshot?.generatedAt) { _, _ in recalculate() }
    }

    private func controls(_ dataset: ResearchDataset) -> some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 17) {
                Eyebrow(text: "Build your perspective")
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], alignment: .leading, spacing: 9) {
                    ForEach(dataset.series) { item in
                        selectionButton(id: item.id, title: item.name, locked: item.id == "INNOVATION_LEADER")
                    }
                }
                if !availableETFs.isEmpty {
                    Text("Overlay an ETF · Market Price + reinvested distributions")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 68))], spacing: 8) {
                        ForEach(availableETFs) { item in selectionButton(id: item.id, title: item.id) }
                    }
                } else {
                    Text("Refresh Compare to make published ETF histories available here. Research remains available offline.")
                        .font(.caption).foregroundStyle(HetzerkTheme.muted)
                }
                Picker("Research period", selection: $period) {
                    ForEach(ResearchPeriod.allCases) { item in Text(item.title).tag(item) }
                }
                .pickerStyle(.segmented).accessibilityIdentifier("research-period")
                Picker("Chart scale", selection: $logarithmic) {
                    Text("Log returns").tag(true)
                    Text("Linear").tag(false)
                }
                .pickerStyle(.segmented).accessibilityIdentifier("research-scale")
                Text("Source levels already include their unspecified backtest assumptions. No extra dividends or fees are applied.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }

    private func selectionButton(id: String, title: String, locked: Bool = false) -> some View {
        let selected = selectedIDs.contains(id)
        return Button {
            if selected { selectedIDs.removeAll { $0 == id } } else { selectedIDs.append(id) }
        } label: {
            HStack(spacing: 7) {
                Circle().fill(ResearchDisplay.color(id)).frame(width: 7, height: 7)
                Text(title).font(.caption.weight(selected ? .semibold : .regular))
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
                if selected { Image(systemName: locked ? "lock.fill" : "checkmark").font(.system(size: 9)) }
            }
            .padding(.horizontal, 10).frame(minHeight: 44)
            .background(selected ? HetzerkTheme.ivory.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(HetzerkTheme.ivory.opacity(selected ? 0.24 : 0.08)))
            .foregroundStyle(selected ? HetzerkTheme.ivory : HetzerkTheme.muted)
        }
        .buttonStyle(.plain).disabled(locked)
        .accessibilityLabel(title).accessibilityValue(selected ? "Selected" : "Not selected")
        .accessibilityIdentifier("research-series-\(id)")
    }

    private func sourceNotes(_ dataset: ResearchDataset) -> some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 13) {
                Eyebrow(text: "Read the evidence")
                Text("Monthly source history").font(.system(.title3, design: .serif))
                Text("\(dataset.period.start) — \(dataset.period.end)")
                    .font(.caption.monospaced()).accessibilityIdentifier("research-source-period")
                Text(dataset.source.title).font(.subheadline)
                Text(dataset.source.precision + ". " + dataset.source.provenance)
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
                DisclosureGroup("Methods & limits") {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(dataset.methodology, id: \.self) { text in Text(text) }
                        Text("ETF overlays use their own complete available daily price-and-distribution history before taking the last observation in each calendar month. A closing observation must be within four calendar days of month end, and the month must have ended by the snapshot's publication day. The actual session date is retained in the inspector. All selected series are then rebased to $100 on their first shared month; no missing history is filled.")
                        Text("CAGR uses elapsed calendar days / 365.25 and is withheld for windows shorter than one calendar year. Month-end drawdown measures declines only across the shared observations; daily and intramonth losses may have been larger. No volatility or correlation estimate is inferred from this monthly archive.")
                        Text("The Log returns view plots growth of $100 on a logarithmic axis. It is not a sequence of logarithmic return increments. The Linear view changes only the axis.")
                        Text("Source SHA-256: " + dataset.source.sha256).font(.caption2.monospaced()).textSelection(.enabled)
                    }
                    .font(.caption).foregroundStyle(HetzerkTheme.muted).padding(.top, 12)
                }
                .font(.subheadline).accessibilityIdentifier("research-methods")
                Link("Read the research ↗", destination: URL(string: "https://oftarradiddle.github.io/RED/research/the-measure-of-fire.html")!)
                    .font(.subheadline)
                Text("Past hypothetical results do not predict future returns. The source portfolio-level backtest has not been independently verified.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }

    private func load() {
        do {
            guard let url = Bundle.main.url(forResource: "strategy_research", withExtension: "json") else {
                throw ResearchError.invalidSource("The offline research archive could not be found in this app build.")
            }
            dataset = try JSONDecoder().decode(ResearchDataset.self, from: Data(contentsOf: url)).validated()
            recalculate()
        } catch { errorMessage = error.localizedDescription }
    }

    private func recalculate() {
        guard let dataset else { return }
        do {
            result = try ResearchEngine.compare(dataset: dataset, selectedIDs: selectedIDs, snapshot: store.snapshot, period: period)
            selectedDate = nil
            errorMessage = nil
        } catch { result = nil; errorMessage = error.localizedDescription }
    }
}

private struct ResearchChartCard: View {
    let result: ResearchResult
    let logarithmic: Bool
    @Binding var selectedDate: Date?

    private var selectedDay: String? {
        guard let selectedDate else { return result.end }
        return result.dates.min { abs(ResearchDisplay.date($0).timeIntervalSince(selectedDate)) < abs(ResearchDisplay.date($1).timeIntervalSince(selectedDate)) }
    }
    private var yDomain: ClosedRange<Double> {
        let values = result.series.flatMap { $0.points.map(\.value) }
        let low = values.min() ?? 100, high = values.max() ?? 100
        return (logarithmic ? max(low * 0.8, 0.000001) : 0)...max(high * 1.12, 110)
    }

    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 17) {
                Eyebrow(text: "\(result.dates.count) shared month ends")
                Text(logarithmic ? "Log returns" : "Growth of $100")
                    .font(.system(.title2, design: .serif)).accessibilityIdentifier("research-chart-title")
                Text(logarithmic ? "Growth of $100 · Logarithmic scale" : "Growth of $100 · Linear scale")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
                Text("\(result.start ?? "—") — \(result.end ?? "—")")
                    .font(.caption.monospaced()).foregroundStyle(HetzerkTheme.muted)
                    .accessibilityIdentifier("research-window")
                chart
                Text("Touch the chart to inspect a month. Each series begins at $100 on the shared start date.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
                if let selectedDay {
                    Divider()
                    Text("Month end · \(selectedDay)").font(.caption.monospaced())
                        .accessibilityIdentifier("research-inspected-date")
                    ForEach(result.series) { item in
                        if let point = item.points.first(where: { $0.date == selectedDay }) {
                            HStack(alignment: .top) {
                                Circle().fill(ResearchDisplay.color(item.id)).frame(width: 7, height: 7).padding(.top, 5)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(item.name).font(.caption.weight(.medium))
                                    if !item.isResearch {
                                        Text("ETF session · \(point.observedDate)").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                                    }
                                }
                                Spacer()
                                Text(ResearchDisplay.money(point.value)).font(.caption.monospaced())
                            }
                        }
                    }
                }
            }
        }
    }

    private var chart: some View {
        Chart {
            ForEach(result.series) { item in
                ForEach(item.points, id: \.date) { point in
                    LineMark(x: .value("Month", ResearchDisplay.date(point.date)), y: .value("Growth of $100", point.value))
                        .foregroundStyle(by: .value("Series", item.id))
                        .lineStyle(StrokeStyle(lineWidth: item.id == "INNOVATION_LEADER" ? 2.8 : 1.6))
                        .interpolationMethod(.linear)
                }
                if let selectedDay, let point = item.points.first(where: { $0.date == selectedDay }) {
                    PointMark(x: .value("Month", ResearchDisplay.date(point.date)), y: .value("Growth of $100", point.value))
                        .foregroundStyle(by: .value("Series", item.id)).symbolSize(26)
                }
            }
            if let selectedDay {
                RuleMark(x: .value("Selected month", ResearchDisplay.date(selectedDay)))
                    .foregroundStyle(HetzerkTheme.ivory.opacity(0.22)).lineStyle(StrokeStyle(dash: [3, 4]))
            }
        }
        .chartForegroundStyleScale(domain: result.series.map(\.id), range: result.series.map { ResearchDisplay.color($0.id) })
        .chartYScale(domain: yDomain, type: logarithmic ? .log : .linear)
        .chartLegend(.hidden)
        .chartXSelection(value: $selectedDate)
        .chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) }
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 5)) { value in
                AxisGridLine().foregroundStyle(HetzerkTheme.ivory.opacity(0.08))
                AxisValueLabel {
                    if let amount = value.as(Double.self) { Text(amount.formatted(.number.notation(.compactName))) }
                }
            }
        }
        .frame(height: 255)
        .accessibilityLabel("Strategy research, growth of 100 dollars, \(logarithmic ? "logarithmic" : "linear") scale")
        .accessibilityIdentifier("research-chart")
    }
}

private struct ResearchResultsCard: View {
    let result: ResearchResult
    var body: some View {
        SculptedCard {
            VStack(alignment: .leading, spacing: 18) {
                Eyebrow(text: "The same window, measured")
                ForEach(result.series) { item in
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Circle().fill(ResearchDisplay.color(item.id)).frame(width: 7, height: 7)
                            Text(item.name).font(.subheadline.weight(.medium))
                            Spacer()
                            Text(item.isResearch ? "Research" : "ETF").font(.caption2).foregroundStyle(HetzerkTheme.muted)
                        }
                        HStack(alignment: .top, spacing: 8) {
                            metric("Change", value: item.metrics.change)
                            metric("CAGR", value: item.metrics.cagr)
                            metric("Month-end\ndrawdown", value: item.metrics.drawdown)
                        }
                        if item.id != result.series.last?.id { Divider() }
                    }
                }
                Text("CAGR uses actual elapsed years and requires at least one calendar year. Drawdown is measured only at matched month ends; intramonth losses may have been larger.")
                    .font(.caption).foregroundStyle(HetzerkTheme.muted)
            }
        }
    }
    private func metric(_ title: String, value: Double?) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(ResearchDisplay.percent(value)).font(.system(.headline, design: .monospaced))
            Text(title).font(.caption2).foregroundStyle(HetzerkTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
