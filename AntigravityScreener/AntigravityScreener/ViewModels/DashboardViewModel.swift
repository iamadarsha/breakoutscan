import Foundation

@Observable
class DashboardViewModel {
    var indices: [IndexData] = []
    var scanHits: [LatestScanHit] = []
    var watchlistCount = 0
    var alertCount = 0
    var isLoading = false
    var error: String?

    private var pollTask: Task<Void, Never>?

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            await loadAll()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(AppConfig.dashboardPollInterval))
                await loadAll()
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
    }

    func loadAll() async {
        do {
            async let idx = APIClient.shared.getIndices()
            async let hits = APIClient.shared.getLatestResults()
            async let wl = APIClient.shared.getWatchlist()
            async let al = APIClient.shared.getAlerts()

            let (i, h, w, a) = try await (idx, hits, wl, al)
            indices = i
            scanHits = h.results
            watchlistCount = w.count
            alertCount = a.count
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}
