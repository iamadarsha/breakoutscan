import SwiftUI

struct AIPicksView: View {
    @State private var vm = AIPicksViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Timeframe Picker
                    Picker("Timeframe", selection: $vm.selectedTimeframe) {
                        ForEach(AIPicksViewModel.AITimeframe.allCases, id: \.self) { tf in
                            Label(tf.rawValue, systemImage: tf.icon)
                                .tag(tf)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    // Subtitle
                    HStack {
                        Image(systemName: vm.selectedTimeframe.icon)
                            .foregroundColor(E8.accent)
                        Text(vm.selectedTimeframe.subtitle)
                            .font(.caption)
                            .foregroundColor(E8.textSecondary)
                        Spacer()
                        if let gen = vm.suggestions?.generatedAt {
                            Text(formatTime(gen))
                                .font(.caption2)
                                .foregroundColor(E8.textMuted)
                        }
                    }
                    .padding(.horizontal)

                    if vm.isLoading {
                        loadingView
                    } else if let err = vm.errorMessage {
                        errorView(err)
                    } else if vm.currentPicks.isEmpty {
                        emptyView
                    } else {
                        // Pick Cards
                        ForEach(Array(vm.currentPicks.enumerated()), id: \.offset) { idx, pick in
                            AIPickCard(pick: pick, index: idx + 1)
                        }
                    }

                    // Disclaimer
                    disclaimerView
                        .padding(.top, 8)
                }
                .padding(.vertical)
            }
            .background(E8.bgPrimary)
            .navigationTitle("AI Picks")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await vm.refresh() }
                    } label: {
                        if vm.isRefreshing {
                            ProgressView()
                                .tint(E8.accent)
                        } else {
                            Image(systemName: "arrow.clockwise")
                                .foregroundColor(E8.accent)
                        }
                    }
                    .disabled(vm.isRefreshing)
                }
            }
            .task { await vm.load() }
        }
    }

    // MARK: - Subviews

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .scaleEffect(1.5)
                .tint(E8.accent)
            Text("AI is analyzing market data...")
                .font(.subheadline.weight(.semibold))
                .foregroundColor(E8.accent)
            Text("Gathering news & generating picks")
                .font(.caption)
                .foregroundColor(E8.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.largeTitle)
                .foregroundColor(E8.amber)
            Text(message)
                .font(.subheadline.weight(.semibold))
                .foregroundColor(E8.amber)
            Button("Retry") {
                Task { await vm.load() }
            }
            .buttonStyle(.borderedProminent)
            .tint(E8.accent)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    private var emptyView: some View {
        VStack(spacing: 12) {
            Image(systemName: "brain.head.profile")
                .font(.largeTitle)
                .foregroundColor(E8.textMuted)
            Text("No picks for \(vm.selectedTimeframe.rawValue)")
                .font(.subheadline.weight(.semibold))
                .foregroundColor(E8.textSecondary)
            Text("Tap refresh to generate new suggestions")
                .font(.caption)
                .foregroundColor(E8.textMuted)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    private var disclaimerView: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "exclamationmark.triangle")
                .font(.caption)
                .foregroundColor(E8.amber)
            Text("AI-generated suggestions for educational purposes only. Not financial advice. Always do your own research.")
                .font(.caption2)
                .foregroundColor(E8.amber.opacity(0.8))
        }
        .padding(12)
        .background(E8.amber.opacity(0.06))
        .cornerRadius(10)
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(E8.amber.opacity(0.2)))
        .padding(.horizontal)
    }

    private func formatTime(_ iso: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: iso) ?? ISO8601DateFormatter().date(from: iso) else { return "" }
        let df = DateFormatter()
        df.dateFormat = "d MMM, h:mm a"
        return df.string(from: date)
    }
}

// MARK: - Pick Card

struct AIPickCard: View {
    let pick: AIPick
    let index: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 8) {
                        Text(pick.symbol)
                            .font(.headline.weight(.heavy))
                            .foregroundColor(E8.accent)

                        Text(pick.action)
                            .font(.caption.weight(.bold))
                            .foregroundColor(pick.action == "BUY" ? E8.bgPrimary : .white)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(pick.action == "BUY" ? E8.green : E8.red)
                            .cornerRadius(6)
                    }
                    Text(pick.companyName)
                        .font(.caption)
                        .foregroundColor(E8.textSecondary)
                        .lineLimit(1)
                }

                Spacer()

                // Confidence
                VStack(spacing: 2) {
                    Text("\(pick.confidence)%")
                        .font(.title3.weight(.heavy))
                        .foregroundColor(confidenceColor)
                    Text("confidence")
                        .font(.system(size: 9))
                        .foregroundColor(E8.textMuted)
                }
            }

            // Target / Stop Loss / Risk:Reward
            HStack(spacing: 0) {
                metricCell(title: "TARGET", value: "+\(String(format: "%.1f", pick.targetPct))%", color: E8.green)
                Divider().background(E8.border).frame(height: 30)
                metricCell(title: "STOP LOSS", value: "-\(String(format: "%.1f", pick.stopLossPct))%", color: E8.red)
                Divider().background(E8.border).frame(height: 30)
                metricCell(title: "R:R", value: "1:\(String(format: "%.1f", pick.targetPct / max(pick.stopLossPct, 0.1)))", color: E8.accent)
            }
            .padding(10)
            .background(E8.bgPrimary)
            .cornerRadius(8)

            // Reasoning
            Text(pick.reasoning)
                .font(.caption)
                .foregroundColor(E8.textSecondary)
                .lineLimit(3)

            // Tags
            HStack(spacing: 6) {
                ForEach(pick.tags, id: \.self) { tag in
                    Text(tag)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(E8.accent)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(E8.accent.opacity(0.12))
                        .cornerRadius(6)
                }
            }
        }
        .padding(16)
        .background(E8.bgCard)
        .cornerRadius(14)
        .overlay(
            VStack {
                Rectangle()
                    .fill(pick.action == "BUY"
                        ? LinearGradient(colors: [E8.green, E8.accent], startPoint: .leading, endPoint: .trailing)
                        : LinearGradient(colors: [E8.red, E8.amber], startPoint: .leading, endPoint: .trailing))
                    .frame(height: 3)
                Spacer()
            }
            .cornerRadius(14)
        )
        .padding(.horizontal)
    }

    private var confidenceColor: Color {
        pick.confidence >= 80 ? E8.green : pick.confidence >= 65 ? E8.amber : E8.textSecondary
    }

    private func metricCell(title: String, value: String, color: Color) -> some View {
        VStack(spacing: 3) {
            Text(title)
                .font(.system(size: 9, weight: .semibold))
                .foregroundColor(E8.textMuted)
            Text(value)
                .font(.callout.weight(.bold))
                .foregroundColor(color)
        }
        .frame(maxWidth: .infinity)
    }
}
