import SwiftUI

struct PriceChangeView: View {
    let changePct: Double

    var body: some View {
        HStack(spacing: 2) {
            Image(systemName: changePct >= 0 ? "arrowtriangle.up.fill" : "arrowtriangle.down.fill")
                .font(.system(size: 8))
            Text(String(format: "%.2f%%", abs(changePct)))
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
        }
        .foregroundColor(changePct >= 0 ? E8.green : E8.red)
    }
}

struct RSIBarView: View {
    let value: Double

    var color: Color {
        if value > 65 { return E8.amber }
        if value < 35 { return E8.green }
        return E8.accent
    }

    var body: some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(String(format: "%.1f", value))
                .font(.system(size: 11, weight: .medium, design: .monospaced))
                .foregroundColor(color)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(E8.border)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(color)
                        .frame(width: geo.size.width * min(value / 100, 1))
                }
            }
            .frame(width: 40, height: 4)
        }
    }
}

struct BadgeView: View {
    let text: String
    var color: Color = E8.accent

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 9, weight: .bold))
            .foregroundColor(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
    }
}

struct CardBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(E8.bgCard)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(E8.border, lineWidth: 1)
            )
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardBackground())
    }
}

func formatPrice(_ n: Double) -> String {
    "₹" + String(format: "%.2f", n)
}

func formatVolume(_ n: Int) -> String {
    if n >= 10_000_000 { return String(format: "%.1fCr", Double(n) / 10_000_000) }
    if n >= 100_000 { return String(format: "%.1fL", Double(n) / 100_000) }
    return String(format: "%.0fK", Double(n) / 1000)
}
