import SwiftUI

enum E8 {
    static let bgPrimary = Color(hex: "0E0F14")
    static let bgCard = Color(hex: "1A1B23")
    static let bgCardHover = Color(hex: "22232D")
    static let bgSidebar = Color(hex: "13141A")

    static let accent = Color(hex: "7C5CFC")
    static let green = Color(hex: "00C896")
    static let red = Color(hex: "FF4757")
    static let amber = Color(hex: "FFB800")

    static let textPrimary = Color(hex: "EEEEF5")
    static let textSecondary = Color(hex: "9899A8")
    static let textMuted = Color(hex: "555666")
    static let border = Color(hex: "2A2B35")
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(.sRGB, red: Double(r) / 255, green: Double(g) / 255, blue: Double(b) / 255, opacity: Double(a) / 255)
    }
}
