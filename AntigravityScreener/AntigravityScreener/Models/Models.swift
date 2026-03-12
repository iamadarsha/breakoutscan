import Foundation

struct IndexData: Codable, Identifiable {
    var id: String { name }
    let name: String
    let ltp: Double
    let change: Double
    let changePct: Double
    let open: Double?
    let high: Double?
    let low: Double?
    let advances: Int?
    let declines: Int?
}

struct MarketStatus: Codable {
    let isOpen: Bool
    let session: String
    let message: String
}

struct PrebuiltScan: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let icon: String
    let category: String
    let timeframe: String
    let badgeColor: String
}

struct ScanResult: Codable, Identifiable {
    var id: String { symbol + (scanTriggeredAt ?? "") }
    let symbol: String
    let companyName: String?
    let ltp: Double
    let changePct: Double
    let volume: Int
    let volumeRatio: Double?
    let rsi14: Double?
    let emaStatus: String?
    let matchedConditions: [String]?
    let scanTriggeredAt: String?
    let sector: String?
    let marketCap: Int?
}

struct ScanRunResponse: Codable {
    let scanName: String
    let timeframe: String
    let results: [ScanResult]
    let resultCount: Int
    let durationMs: Int
    let runAt: String
}

struct LatestResultsResponse: Codable {
    let results: [LatestScanHit]
    let total: Int
}

struct LatestScanHit: Codable, Identifiable {
    var id: String { symbol + scanId }
    let symbol: String
    let scanName: String
    let scanId: String
    let ltp: Double
    let changePct: Double
    let volume: Int
    let rsi14: Double?
    let triggeredAt: String?
}

struct WatchlistItem: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let companyName: String?
    let ltp: Double
    let changePct: Double
    let volume: Int
    let rsi14: Double?
    let ema20Status: String?
    let sector: String?
}

struct AlertItem: Codable, Identifiable {
    let id: String
    let symbol: String
    let scanName: String
    let notifyPush: Bool?
    let notifyTelegram: Bool?
    let isActive: Bool
    let frequency: String?
    let createdAt: String?
}

struct AlertHistoryItem: Codable, Identifiable {
    let id: String
    let symbol: String
    let scanName: String
    let triggerPrice: Double?
    let triggeredAt: String?
    let conditionsMet: [String]?
}

struct OHLCVBar: Codable, Identifiable {
    var id: String { ts }
    let ts: String
    let open: Double
    let high: Double
    let low: Double
    let close: Double
    let volume: Int
}

struct OHLCVResponse: Codable {
    let symbol: String
    let timeframe: String
    let bars: [OHLCVBar]
}

struct LivePrice: Codable {
    let symbol: String
    let ltp: Double
    let open: Double?
    let high: Double?
    let low: Double?
    let prevClose: Double?
    let change: Double?
    let changePct: Double?
    let volume: Int?
}

struct StockSearchResult: Codable, Identifiable {
    var id: String { symbol }
    let symbol: String
    let companyName: String?
    let exchange: String?
    let instrumentKey: String?
}

struct AlertCreateRequest: Codable {
    let symbol: String
    let scanName: String
    let notifyPush: Bool
    let notifyTelegram: Bool
    let frequency: String
}
