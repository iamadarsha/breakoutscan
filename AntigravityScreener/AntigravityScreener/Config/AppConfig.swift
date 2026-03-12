import Foundation

enum AppConfig {
    // Production (Render hosted) — switch to local for development
    #if DEBUG
    static let baseURL = "http://192.168.1.190:8002"
    static let wsURL = "ws://192.168.1.190:8002"
    #else
    static let baseURL = "https://breakoutscan-api.onrender.com"
    static let wsURL = "wss://breakoutscan-api.onrender.com"
    #endif

    static let indexPollInterval: TimeInterval = 5
    static let dashboardPollInterval: TimeInterval = 10
    static let watchlistPollInterval: TimeInterval = 8
    static let chartPollInterval: TimeInterval = 5
}
