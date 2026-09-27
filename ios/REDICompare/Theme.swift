import SwiftUI

enum HetzerkTheme {
    static let ink = Color(red: 23 / 255, green: 22 / 255, blue: 23 / 255)
    static let ivory = Color(red: 243 / 255, green: 238 / 255, blue: 229 / 255)
    static let red = Color(red: 139 / 255, green: 0, blue: 0)
    static let surface = Color(red: 34 / 255, green: 31 / 255, blue: 32 / 255)
    static let raised = Color(red: 44 / 255, green: 40 / 255, blue: 41 / 255)
    static let muted = Color(red: 185 / 255, green: 179 / 255, blue: 173 / 255)
    static let yellow = Color(red: 244 / 255, green: 218 / 255, blue: 104 / 255)

    static let seriesColors: [Color] = [
        Color(red: 246 / 255, green: 103 / 255, blue: 96 / 255),
        ivory,
        Color(red: 214 / 255, green: 181 / 255, blue: 117 / 255),
        Color(red: 147 / 255, green: 179 / 255, blue: 178 / 255),
        Color(red: 177 / 255, green: 159 / 255, blue: 204 / 255),
        Color(red: 161 / 255, green: 188 / 255, blue: 137 / 255)
    ]

    static func color(for symbol: String) -> Color {
        let symbols = ["REDI", "SPY", "VOO", "QQQ", "ITAN", "SYLD"]
        return seriesColors[symbols.firstIndex(of: symbol) ?? 0]
    }
}

/// The two swept wings use the same geometry as the site's original H mark.
struct WingHShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: 150, y: 122))
        path.addQuadCurve(to: CGPoint(x: 142, y: 126), control: CGPoint(x: 143, y: 113))
        path.addLine(to: CGPoint(x: 140, y: 363))
        path.addQuadCurve(to: CGPoint(x: 149, y: 364), control: CGPoint(x: 140, y: 378))
        path.addLine(to: CGPoint(x: 215, y: 245))
        path.addQuadCurve(to: CGPoint(x: 215, y: 232), control: CGPoint(x: 219, y: 238))
        path.closeSubpath()
        path.move(to: CGPoint(x: 334, y: 122))
        path.addQuadCurve(to: CGPoint(x: 342, y: 126), control: CGPoint(x: 341, y: 113))
        path.addLine(to: CGPoint(x: 340, y: 363))
        path.addQuadCurve(to: CGPoint(x: 331, y: 364), control: CGPoint(x: 340, y: 378))
        path.addLine(to: CGPoint(x: 266, y: 245))
        path.addQuadCurve(to: CGPoint(x: 266, y: 232), control: CGPoint(x: 262, y: 238))
        path.closeSubpath()
        let side = min(rect.width, rect.height)
        return path.applying(CGAffineTransform(scaleX: side / 480, y: side / 480))
            .applying(CGAffineTransform(translationX: (rect.width - side) / 2,
                                       y: (rect.height - side) / 2))
    }
}

struct WingHMark: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var lifted = false
    var size: CGFloat = 36
    var animated = true

    var body: some View {
        WingHShape()
            .fill(HetzerkTheme.red)
            .frame(width: size, height: size)
            .background(HetzerkTheme.ivory, in: RoundedRectangle(cornerRadius: size * 0.19))
            .offset(y: lifted && !reduceMotion ? -2 : 0)
            .animation(reduceMotion || !animated ? nil : .easeInOut(duration: 1.6).repeatForever(autoreverses: true), value: lifted)
            .onAppear { lifted = animated && !reduceMotion }
            .onChange(of: reduceMotion) { _, value in lifted = animated && !value }
            .accessibilityHidden(true)
    }
}

struct SculptedCard<Content: View>: View {
    var padding: CGFloat = 20
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background {
                RoundedRectangle(cornerRadius: 23)
                    .fill(LinearGradient(colors: [HetzerkTheme.raised, HetzerkTheme.surface],
                                         startPoint: .topLeading, endPoint: .bottomTrailing))
                    .overlay {
                        RoundedRectangle(cornerRadius: 23)
                            .strokeBorder(LinearGradient(colors: [.white.opacity(0.13), .white.opacity(0.025)],
                                                         startPoint: .topLeading, endPoint: .bottomTrailing))
                    }
                    .shadow(color: .black.opacity(0.2), radius: 13, x: 0, y: 8)
            }
    }
}

struct Eyebrow: View {
    var text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(.caption2, design: .monospaced).weight(.semibold))
            .tracking(1.6)
            .foregroundStyle(HetzerkTheme.muted)
    }
}

struct PageHeading: View {
    var eyebrow: String
    var title: String
    var subtitle: String
    var body: some View {
        VStack(alignment: .leading, spacing: 11) {
            Eyebrow(text: eyebrow)
            Text(title)
                .font(.system(.largeTitle, design: .serif).weight(.regular))
                .foregroundStyle(HetzerkTheme.ivory)
                .fixedSize(horizontal: false, vertical: true)
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(HetzerkTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 14)
    }
}
