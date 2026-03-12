import SwiftUI

struct WatchlistView: View {
    @State private var vm = WatchlistViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    if vm.items.isEmpty {
                        VStack(spacing: 12) {
                            Text("⭐")
                                .font(.system(size: 40))
                            Text("Your watchlist is empty")
                                .font(.system(size: 15, weight: .semibold))
                            Text("Tap + to add stocks")
                                .font(.system(size: 13))
                                .foregroundColor(E8.textSecondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 60)
                    } else {
                        // Header
                        HStack {
                            Text("Your Watchlist")
                                .font(.system(size: 15, weight: .bold))
                            BadgeView(text: "\(vm.items.count)", color: E8.green)
                            Spacer()
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)

                        ForEach(vm.items) { item in
                            WatchlistRow(item: item)
                                .swipeActions(edge: .trailing) {
                                    Button(role: .destructive) {
                                        Task { await vm.removeStock(item.symbol) }
                                    } label: {
                                        Label("Remove", systemImage: "trash")
                                    }
                                }
                            Divider().background(E8.border)
                        }
                    }
                }
                .cardStyle()
                .padding()

                // Quick add
                VStack(alignment: .leading, spacing: 8) {
                    Text("POPULAR STOCKS")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(E8.textSecondary)
                        .tracking(0.5)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(["RELIANCE", "INFY", "BAJFINANCE", "WIPRO", "TCS"], id: \.self) { sym in
                                Button {
                                    Task { await vm.addStock(sym) }
                                } label: {
                                    Text("+ \(sym)")
                                        .font(.system(size: 12, weight: .medium))
                                        .foregroundColor(E8.accent)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 8)
                                        .background(E8.accent.opacity(0.1))
                                        .clipShape(Capsule())
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal)
            }
            .background(E8.bgPrimary)
            .navigationTitle("Watchlist")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        vm.showAddSheet = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .foregroundColor(E8.accent)
                    }
                }
            }
            .sheet(isPresented: $vm.showAddSheet) {
                AddStockSheet(vm: vm)
            }
            .onAppear { vm.startPolling() }
            .onDisappear { vm.stopPolling() }
        }
    }
}

struct WatchlistRow: View {
    let item: WatchlistItem

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.symbol)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(E8.accent)
                Text(item.companyName ?? item.sector ?? "NSE")
                    .font(.system(size: 10))
                    .foregroundColor(E8.textSecondary)
                    .lineLimit(1)
            }
            .frame(width: 90, alignment: .leading)

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(formatPrice(item.ltp))
                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                PriceChangeView(changePct: item.changePct)
            }

            if let rsi = item.rsi14 {
                RSIBarView(value: rsi)
            }

            if let ema = item.ema20Status {
                BadgeView(text: ema, color: ema.contains("Above") ? E8.green : E8.red)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}

struct AddStockSheet: View {
    @Bindable var vm: WatchlistViewModel
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                TextField("Search symbol or company...", text: $vm.searchQuery)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(E8.bgPrimary)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(E8.border))
                    .onChange(of: vm.searchQuery) {
                        Task { await vm.search() }
                    }

                List(vm.searchResults) { result in
                    Button {
                        Task {
                            await vm.addStock(result.symbol)
                            dismiss()
                        }
                    } label: {
                        HStack {
                            Text(result.symbol)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(E8.accent)
                            Text(result.companyName ?? "")
                                .font(.system(size: 12))
                                .foregroundColor(E8.textSecondary)
                            Spacer()
                            Image(systemName: "plus.circle")
                                .foregroundColor(E8.green)
                        }
                    }
                    .listRowBackground(E8.bgCard)
                }
                .listStyle(.plain)
            }
            .padding()
            .background(E8.bgPrimary)
            .navigationTitle("Add Stock")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(E8.accent)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}
