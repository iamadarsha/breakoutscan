import Foundation

@Observable
class ChartViewModel {
    var symbol = "RELIANCE"
    var timeframe = "15min"
    var bars: [OHLCVBar] = []
    var price: LivePrice?
    var isLoading = false

    let defaultSymbols = ["RELIANCE", "HDFCBANK", "TATAMOTORS", "WIPRO", "ICICIBANK", "TCS", "INFY"]
    let timeframes = ["1min", "5min", "15min", "30min", "1hr", "daily"]

    private var pollTask: Task<Void, Never>?

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            await loadData()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(AppConfig.chartPollInterval))
                await loadData()
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
    }

    func loadData() async {
        isLoading = bars.isEmpty
        do {
            async let ohlcv = APIClient.shared.getOHLCV(symbol: symbol, tf: timeframe)
            async let lp = APIClient.shared.getPrice(symbol: symbol)
            let (o, p) = try await (ohlcv, lp)
            bars = o.bars
            price = p
        } catch {
            print("Chart load error: \(error)")
        }
        isLoading = false
    }

    func switchSymbol(_ sym: String) {
        symbol = sym
        bars = []
        price = nil
        startPolling()
    }

    func switchTimeframe(_ tf: String) {
        timeframe = tf
        bars = []
        startPolling()
    }
}
