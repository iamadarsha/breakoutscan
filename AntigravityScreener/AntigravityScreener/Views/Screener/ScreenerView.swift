import SwiftUI

struct ScreenerView: View {
    @State private var vm = ScreenerViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Scan Cards Grid
                    VStack(alignment: .leading, spacing: 8) {
                        Text("PRE-BUILT SCANNERS")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(E8.textSecondary)
                            .tracking(0.5)
                            .padding(.horizontal)

                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(vm.scans) { scan in
                                ScanCardView(scan: scan, isActive: vm.activeScanId == scan.id)
                                    .onTapGesture {
                                        Task { await vm.runScan(scan) }
                                    }
                            }
                        }
                        .padding(.horizontal)
                    }

                    // Results
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            if let name = vm.activeScanName {
                                Text(name)
                                    .font(.system(size: 15, weight: .bold))
                                if !vm.results.isEmpty {
                                    BadgeView(text: "\(vm.results.count) results", color: E8.green)
                                }
                                if vm.durationMs > 0 {
                                    Text("in \(vm.durationMs)ms")
                                        .font(.system(size: 11))
                                        .foregroundColor(E8.textMuted)
                                }
                            } else {
                                Text("Tap a scan above to run it")
                                    .font(.system(size: 14))
                                    .foregroundColor(E8.textSecondary)
                            }
                            Spacer()
                        }
                        .padding(.horizontal)

                        if vm.isScanning {
                            VStack(spacing: 12) {
                                ProgressView()
                                    .tint(E8.accent)
                                Text("Scanning 2000+ stocks...")
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundColor(E8.accent)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 40)
                        } else if vm.activeScanName != nil && vm.results.isEmpty {
                            Text("🔍 No stocks matched this scan")
                                .font(.system(size: 13))
                                .foregroundColor(E8.textSecondary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 40)
                        } else {
                            ForEach(vm.results) { result in
                                ScanResultRow(result: result)
                            }
                        }
                    }
                    .padding(.vertical, 12)
                    .cardStyle()
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(E8.bgPrimary)
            .navigationTitle("Screener")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .task { await vm.loadScans() }
        }
    }
}

struct ScanCardView: View {
    let scan: PrebuiltScan
    let isActive: Bool

    var categoryColor: Color {
        switch scan.category {
        case "Pattern": return E8.amber
        case "Breakout": return E8.accent
        case "RSI": return E8.green
        case "Volume": return E8.red
        case "Trend", "Volatility", "Momentum": return E8.accent
        case "Intraday": return E8.green
        case "VWAP": return E8.green
        default: return E8.accent
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Text(scan.icon)
                    .font(.system(size: 16))
                Text(scan.name)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(E8.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Text(scan.description)
                .font(.system(size: 10))
                .foregroundColor(E8.textSecondary)
                .lineLimit(2)

            HStack(spacing: 6) {
                BadgeView(text: scan.category, color: categoryColor)
                BadgeView(text: scan.timeframe, color: E8.accent)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(isActive ? E8.accent.opacity(0.08) : E8.bgCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isActive ? E8.accent : E8.border, lineWidth: 1)
        )
    }
}

struct ScanResultRow: View {
    let result: ScanResult

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(result.symbol)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(E8.accent)
                Text(result.companyName ?? result.sector ?? "NSE")
                    .font(.system(size: 10))
                    .foregroundColor(E8.textSecondary)
                    .lineLimit(1)
            }
            .frame(width: 90, alignment: .leading)

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(formatPrice(result.ltp))
                    .font(.system(size: 12, weight: .semibold, design: .monospaced))
                PriceChangeView(changePct: result.changePct)
            }

            if let rsi = result.rsi14 {
                RSIBarView(value: rsi)
            }

            if let conditions = result.matchedConditions?.prefix(2) {
                VStack(alignment: .trailing, spacing: 2) {
                    ForEach(Array(conditions), id: \.self) { c in
                        Text("✓ \(c.prefix(10))")
                            .font(.system(size: 8, weight: .medium))
                            .foregroundColor(E8.green)
                    }
                }
                .frame(width: 60)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }
}
