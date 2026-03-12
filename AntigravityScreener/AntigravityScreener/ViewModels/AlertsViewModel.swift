import Foundation

@Observable
class AlertsViewModel {
    var alerts: [AlertItem] = []
    var history: [AlertHistoryItem] = []
    var selectedTab = 0
    var isLoading = false

    func loadAll() async {
        isLoading = true
        do {
            async let a = APIClient.shared.getAlerts()
            async let h = APIClient.shared.getAlertHistory()
            let (al, hi) = try await (a, h)
            alerts = al
            history = hi
        } catch {
            print("Alerts load error: \(error)")
        }
        isLoading = false
    }
}
