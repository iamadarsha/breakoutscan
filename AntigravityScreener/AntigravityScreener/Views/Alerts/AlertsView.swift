import SwiftUI

struct AlertsView: View {
    @State private var vm = AlertsViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Stats
                    HStack(spacing: 12) {
                        AlertStatCard(icon: "🔔", value: "\(vm.alerts.count)", label: "Active", color: E8.amber)
                        AlertStatCard(icon: "⚡", value: "\(vm.history.count)", label: "Triggered", color: E8.green)
                        AlertStatCard(icon: "⏸️", value: "\(vm.alerts.filter { !$0.isActive }.count)", label: "Paused", color: E8.textMuted)
                    }
                    .padding(.horizontal)

                    // Tab picker
                    Picker("", selection: $vm.selectedTab) {
                        Text("Active (\(vm.alerts.count))").tag(0)
                        Text("History (\(vm.history.count))").tag(1)
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    // Content
                    VStack(spacing: 0) {
                        if vm.selectedTab == 0 {
                            if vm.alerts.isEmpty {
                                Text("No active alerts")
                                    .foregroundColor(E8.textSecondary)
                                    .padding(.vertical, 40)
                            } else {
                                ForEach(vm.alerts) { alert in
                                    AlertRow(alert: alert)
                                    Divider().background(E8.border)
                                }
                            }
                        } else {
                            if vm.history.isEmpty {
                                Text("No trigger history")
                                    .foregroundColor(E8.textSecondary)
                                    .padding(.vertical, 40)
                            } else {
                                ForEach(vm.history) { item in
                                    AlertHistoryRow(item: item)
                                    Divider().background(E8.border)
                                }
                            }
                        }
                    }
                    .cardStyle()
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(E8.bgPrimary)
            .navigationTitle("Alerts")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .task { await vm.loadAll() }
        }
    }
}

struct AlertStatCard: View {
    let icon: String
    let value: String
    let label: String
    let color: Color

    var body: some View {
        VStack(spacing: 4) {
            Text(icon).font(.system(size: 20))
            Text(value)
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .foregroundColor(color)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(E8.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .cardStyle()
    }
}

struct AlertRow: View {
    let alert: AlertItem

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(alert.symbol)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(E8.accent)
                Text(alert.scanName)
                    .font(.system(size: 11))
                    .foregroundColor(E8.textSecondary)
            }
            Spacer()
            HStack(spacing: 4) {
                if alert.notifyPush == true {
                    BadgeView(text: "PUSH", color: E8.accent)
                }
                if alert.notifyTelegram == true {
                    BadgeView(text: "TG", color: E8.green)
                }
            }
            BadgeView(text: alert.isActive ? "ACTIVE" : "PAUSED", color: alert.isActive ? E8.green : E8.textMuted)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}

struct AlertHistoryRow: View {
    let item: AlertHistoryItem

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.symbol)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(E8.accent)
                Text(item.scanName)
                    .font(.system(size: 11))
                    .foregroundColor(E8.textSecondary)
            }
            Spacer()
            if let price = item.triggerPrice {
                Text(formatPrice(price))
                    .font(.system(size: 12, weight: .semibold, design: .monospaced))
            }
            if let conditions = item.conditionsMet?.prefix(2) {
                VStack(alignment: .trailing, spacing: 2) {
                    ForEach(Array(conditions), id: \.self) { c in
                        Text("✓ \(c.prefix(12))")
                            .font(.system(size: 9))
                            .foregroundColor(E8.green)
                    }
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}
