import Foundation

@Observable
class AIPicksViewModel {
    var suggestions: AISuggestionsResponse?
    var isLoading = false
    var isRefreshing = false
    var errorMessage: String?
    var selectedTimeframe: AITimeframe = .intraday

    enum AITimeframe: String, CaseIterable {
        case intraday = "Intraday"
        case weekly = "Weekly"
        case monthly = "Monthly"

        var icon: String {
            switch self {
            case .intraday: return "bolt.fill"
            case .weekly: return "chart.line.uptrend.xyaxis"
            case .monthly: return "target"
            }
        }

        var subtitle: String {
            switch self {
            case .intraday: return "Same-day trades"
            case .weekly: return "1-5 day swings"
            case .monthly: return "2-4 week positions"
            }
        }
    }

    var currentPicks: [AIPick] {
        guard let data = suggestions?.suggestions else { return [] }
        switch selectedTimeframe {
        case .intraday: return data.intraday ?? []
        case .weekly: return data.weekly ?? []
        case .monthly: return data.monthly ?? []
        }
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            suggestions = try await APIClient.shared.getAISuggestions()
        } catch {
            errorMessage = "Failed to load AI suggestions"
        }
        isLoading = false
    }

    func refresh() async {
        isRefreshing = true
        errorMessage = nil
        do {
            suggestions = try await APIClient.shared.refreshAISuggestions()
        } catch {
            errorMessage = "Refresh failed"
        }
        isRefreshing = false
    }
}
