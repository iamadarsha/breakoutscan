import Foundation

actor APIClient {
    static let shared = APIClient()

    private let session = URLSession.shared
    private let base = AppConfig.baseURL
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    // MARK: - Generic

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let url = URL(string: "\(base)\(path)")!
        let (data, _) = try await session.data(from: url)
        return try decoder.decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ path: String, body: Data? = nil) async throws -> T {
        let url = URL(string: "\(base)\(path)")!
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        let (data, _) = try await session.data(for: req)
        return try decoder.decode(T.self, from: data)
    }

    private func postVoid(_ path: String, body: Data? = nil) async throws {
        let url = URL(string: "\(base)\(path)")!
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        let _ = try await session.data(for: req)
    }

    private func delete(_ path: String) async throws {
        let url = URL(string: "\(base)\(path)")!
        var req = URLRequest(url: url)
        req.httpMethod = "DELETE"
        let _ = try await session.data(for: req)
    }

    // MARK: - Indices & Market

    func getIndices() async throws -> [IndexData] {
        try await get("/api/indices")
    }

    func getMarketStatus() async throws -> MarketStatus {
        try await get("/api/market/status")
    }

    // MARK: - Screener

    func getPrebuiltScans() async throws -> [PrebuiltScan] {
        try await get("/api/screener/prebuilt")
    }

    func runPrebuiltScan(id: String) async throws -> ScanRunResponse {
        try await post("/api/screener/prebuilt/\(id)/run")
    }

    func getLatestResults() async throws -> LatestResultsResponse {
        try await get("/api/screener/results/latest")
    }

    // MARK: - Watchlist

    func getWatchlist() async throws -> [WatchlistItem] {
        try await get("/api/watchlist")
    }

    func addToWatchlist(symbol: String) async throws {
        try await postVoid("/api/watchlist/\(symbol)")
    }

    func removeFromWatchlist(symbol: String) async throws {
        try await delete("/api/watchlist/\(symbol)")
    }

    // MARK: - Alerts

    func getAlerts() async throws -> [AlertItem] {
        try await get("/api/alerts")
    }

    func getAlertHistory() async throws -> [AlertHistoryItem] {
        try await get("/api/alerts/history")
    }

    func createAlert(_ alert: AlertCreateRequest) async throws {
        let body = try JSONEncoder().encode(alert)
        try await postVoid("/api/alerts", body: body)
    }

    // MARK: - Stocks & Charts

    func getOHLCV(symbol: String, tf: String = "15min", bars: Int = 200) async throws -> OHLCVResponse {
        try await get("/api/stocks/\(symbol)/ohlcv?tf=\(tf)&bars=\(bars)")
    }

    func getPrice(symbol: String) async throws -> LivePrice {
        try await get("/api/prices/\(symbol)")
    }

    func searchStocks(query: String) async throws -> [StockSearchResult] {
        let q = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        return try await get("/api/stocks/search?q=\(q)")
    }

    // MARK: - AI Suggestions

    func getAISuggestions() async throws -> AISuggestionsResponse {
        try await get("/api/ai-suggestions")
    }

    func refreshAISuggestions() async throws -> AISuggestionsResponse {
        try await post("/api/ai-suggestions/refresh")
    }
}
