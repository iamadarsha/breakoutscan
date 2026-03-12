import Foundation

@Observable
class WatchlistViewModel {
    var items: [WatchlistItem] = []
    var searchQuery = ""
    var searchResults: [StockSearchResult] = []
    var isLoading = false
    var showAddSheet = false

    private var pollTask: Task<Void, Never>?

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task {
            await loadWatchlist()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(AppConfig.watchlistPollInterval))
                await loadWatchlist()
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
    }

    func loadWatchlist() async {
        do {
            items = try await APIClient.shared.getWatchlist()
        } catch {
            print("Watchlist load error: \(error)")
        }
    }

    func addStock(_ symbol: String) async {
        do {
            try await APIClient.shared.addToWatchlist(symbol: symbol)
            await loadWatchlist()
        } catch {
            print("Add failed: \(error)")
        }
    }

    func removeStock(_ symbol: String) async {
        do {
            try await APIClient.shared.removeFromWatchlist(symbol: symbol)
            await loadWatchlist()
        } catch {
            print("Remove failed: \(error)")
        }
    }

    func search() async {
        guard searchQuery.count >= 2 else { searchResults = []; return }
        do {
            searchResults = try await APIClient.shared.searchStocks(query: searchQuery)
        } catch {
            print("Search error: \(error)")
        }
    }
}
