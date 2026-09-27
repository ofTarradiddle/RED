import SwiftUI
import REDICore

@main
@MainActor
struct REDICompareApp: App {
    @StateObject private var store: ComparisonStore
    @Environment(\.scenePhase) private var scenePhase

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--ui-testing") {
            let defaults = UserDefaults(suiteName: "com.hetzerk.REDICompare.UITests")!
            defaults.removePersistentDomain(forName: "com.hetzerk.REDICompare.UITests")
            _store = StateObject(wrappedValue: ComparisonStore(defaults: defaults,
                fixtureURL: Bundle.main.url(forResource: "comparison-preview", withExtension: "json")))
            return
        }
        #endif
        _store = StateObject(wrappedValue: ComparisonStore())
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .preferredColorScheme(.dark)
                .task { await store.refresh() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { Task { await store.refresh() } }
                }
        }
    }
}
