import SwiftUI

struct DashboardView: View {
    @State private var vm = DashboardViewModel()
    var onSelectSymbol: ((String) -> Void)?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Index Bar
                    IndexBarView(indices: vm.indices)

                    // Stats Cards
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        StatsCardView(icon: "🔥", title: "Scan Hits", value: "\(vm.scanHits.count)", subtitle: "stocks", color: E8.accent)
                        StatsCardView(icon: "⭐", title: "Watchlist", value: "\(vm.watchlistCount)", subtitle: "stocks", color: E8.amber)
                        StatsCardView(icon: "🔔", title: "Alerts", value: "\(vm.alertCount)", subtitle: "active", color: E8.green)
                        StatsCardView(icon: "📊", title: "Market", value: vm.indices.isEmpty ? "--" : "\(vm.indices.first(where: { $0.name.contains("NIFTY 50") })?.changePct ?? 0 >= 0 ? "+" : "")\(String(format: "%.1f%%", vm.indices.first(where: { $0.name.contains("NIFTY 50") })?.changePct ?? 0))", subtitle: "NIFTY 50", color: (vm.indices.first(where: { $0.name.contains("NIFTY 50") })?.changePct ?? 0) >= 0 ? E8.green : E8.red)
                    }
                    .padding(.horizontal)

                    // Live Scan Hits
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Live Scan Hits")
                                .font(.system(size: 15, weight: .bold))
                            BadgeView(text: "\(vm.scanHits.count) stocks", color: E8.green)
                            Spacer()
                        }
                        .padding(.horizontal)

                        if vm.scanHits.isEmpty {
                            Text("No scan hits yet")
                                .font(.system(size: 13))
                                .foregroundColor(E8.textSecondary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 40)
                        } else {
                            ForEach(vm.scanHits) { hit in
                                ScanHitRow(hit: hit)
                                    .onTapGesture { onSelectSymbol?(hit.symbol) }
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
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .onAppear { vm.startPolling() }
            .onDisappear { vm.stopPolling() }
        }
    }
}

struct IndexBarView: View {
    let indices: [IndexData]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(indices) { idx in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(idx.name)
                            .font(.system(size: 10, weight: .medium))
                            .foregroundColor(E8.textSecondary)
                            .lineLimit(1)
                        Text(String(format: "%.2f", idx.ltp))
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(E8.textPrimary)
                        PriceChangeView(changePct: idx.changePct)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .frame(minWidth: 110)
                    .cardStyle()
                }
            }
            .padding(.horizontal)
        }
    }
}

struct StatsCardView: View {
    let icon: String
    let title: String
    let value: String
    let subtitle: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(icon)
                    .font(.system(size: 16))
                Text(title)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(E8.textSecondary)
            }
            Text(value)
                .font(.system(size: 24, weight: .bold, design: .monospaced))
                .foregroundColor(color)
            Text(subtitle)
                .font(.system(size: 11))
                .foregroundColor(E8.textMuted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .cardStyle()
    }
}

struct ScanHitRow: View {
    let hit: LatestScanHit

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(hit.symbol)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(E8.accent)
                Text(hit.scanName)
                    .font(.system(size: 11))
                    .foregroundColor(E8.textSecondary)
                    .lineLimit(1)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(formatPrice(hit.ltp))
                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                PriceChangeView(changePct: hit.changePct)
            }
            if let rsi = hit.rsi14 {
                RSIBarView(value: rsi)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}
