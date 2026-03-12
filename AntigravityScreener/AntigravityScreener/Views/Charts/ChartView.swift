import SwiftUI
import Charts

struct ChartView: View {
    @State private var vm = ChartViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 12) {
                    // Symbol header
                    if let p = vm.price {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(vm.symbol)
                                    .font(.system(size: 20, weight: .bold))
                                Text("NSE • Equity")
                                    .font(.system(size: 11))
                                    .foregroundColor(E8.textSecondary)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text(formatPrice(p.ltp))
                                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                                PriceChangeView(changePct: p.changePct ?? 0)
                            }
                        }
                        .padding(.horizontal)

                        // OHLC row
                        HStack(spacing: 16) {
                            OHLCItem(label: "O", value: p.open ?? 0)
                            OHLCItem(label: "H", value: p.high ?? 0)
                            OHLCItem(label: "L", value: p.low ?? 0)
                            OHLCItem(label: "C", value: p.ltp)
                            OHLCItem(label: "Vol", value: Double(p.volume ?? 0), isVolume: true)
                        }
                        .padding(.horizontal)
                    }

                    // Timeframe picker
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(vm.timeframes, id: \.self) { tf in
                                Text(tf)
                                    .font(.system(size: 12, weight: vm.timeframe == tf ? .bold : .medium))
                                    .foregroundColor(vm.timeframe == tf ? .black : E8.textSecondary)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 7)
                                    .background(vm.timeframe == tf ? E8.accent : E8.bgCard)
                                    .clipShape(Capsule())
                                    .onTapGesture { vm.switchTimeframe(tf) }
                            }
                        }
                        .padding(.horizontal)
                    }

                    // Candlestick chart
                    if vm.isLoading {
                        ProgressView()
                            .tint(E8.accent)
                            .frame(height: 300)
                    } else if vm.bars.isEmpty {
                        Text("No chart data")
                            .foregroundColor(E8.textSecondary)
                            .frame(height: 300)
                    } else {
                        CandlestickChartView(bars: vm.bars)
                            .frame(height: 300)
                            .padding(.horizontal)

                        // Volume chart
                        VolumeChartView(bars: vm.bars)
                            .frame(height: 60)
                            .padding(.horizontal)
                    }

                    // Symbol quick picker
                    VStack(alignment: .leading, spacing: 8) {
                        Text("SYMBOLS")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(E8.textSecondary)
                            .tracking(0.5)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(vm.defaultSymbols, id: \.self) { sym in
                                    Text(sym)
                                        .font(.system(size: 12, weight: vm.symbol == sym ? .bold : .medium))
                                        .foregroundColor(vm.symbol == sym ? .black : E8.textPrimary)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 8)
                                        .background(vm.symbol == sym ? E8.accent : E8.bgCard)
                                        .clipShape(Capsule())
                                        .overlay(Capsule().stroke(E8.border, lineWidth: 1))
                                        .onTapGesture { vm.switchSymbol(sym) }
                                }
                            }
                        }
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(E8.bgPrimary)
            .navigationTitle("Charts")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .onAppear { vm.startPolling() }
            .onDisappear { vm.stopPolling() }
        }
    }
}

struct OHLCItem: View {
    let label: String
    let value: Double
    var isVolume = false

    var body: some View {
        VStack(spacing: 1) {
            Text(label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(E8.textMuted)
            Text(isVolume ? formatVolume(Int(value)) : String(format: "%.1f", value))
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundColor(E8.textSecondary)
        }
    }
}

struct CandlestickChartView: View {
    let bars: [OHLCVBar]

    var displayBars: [OHLCVBar] {
        Array(bars.suffix(60))
    }

    var body: some View {
        Chart {
            ForEach(Array(displayBars.enumerated()), id: \.offset) { index, bar in
                // Wick
                RuleMark(
                    x: .value("Time", index),
                    yStart: .value("Low", bar.low),
                    yEnd: .value("High", bar.high)
                )
                .foregroundStyle(bar.close >= bar.open ? E8.green : E8.red)
                .lineStyle(StrokeStyle(lineWidth: 1))

                // Body
                RectangleMark(
                    x: .value("Time", index),
                    yStart: .value("Open", bar.open),
                    yEnd: .value("Close", bar.close),
                    width: 4
                )
                .foregroundStyle(bar.close >= bar.open ? E8.green : E8.red)
            }
        }
        .chartXAxis(.hidden)
        .chartYAxis {
            AxisMarks(position: .leading) { value in
                AxisValueLabel {
                    Text(String(format: "%.0f", value.as(Double.self) ?? 0))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundColor(E8.textMuted)
                }
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [4]))
                    .foregroundStyle(E8.border)
            }
        }
        .chartPlotStyle { plot in
            plot.background(E8.bgCard.opacity(0.3))
        }
    }
}

struct VolumeChartView: View {
    let bars: [OHLCVBar]

    var displayBars: [OHLCVBar] {
        Array(bars.suffix(60))
    }

    var body: some View {
        Chart {
            ForEach(Array(displayBars.enumerated()), id: \.offset) { index, bar in
                BarMark(
                    x: .value("Time", index),
                    y: .value("Volume", bar.volume)
                )
                .foregroundStyle(bar.close >= bar.open ? E8.green.opacity(0.4) : E8.red.opacity(0.4))
            }
        }
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
    }
}
