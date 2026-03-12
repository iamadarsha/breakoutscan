import Foundation

@Observable
class WebSocketManager {
    var isConnected = false
    private var priceTask: URLSessionWebSocketTask?
    private var scanTask: URLSessionWebSocketTask?

    func connectPrices(onUpdate: @escaping ([String: Any]) -> Void) {
        guard let url = URL(string: "\(AppConfig.wsURL)/ws/prices") else { return }
        let task = URLSession.shared.webSocketTask(with: url)
        priceTask = task
        task.resume()
        isConnected = true
        receiveLoop(task: task, onMessage: onUpdate)
    }

    func connectScans(onUpdate: @escaping ([String: Any]) -> Void) {
        guard let url = URL(string: "\(AppConfig.wsURL)/ws/scans") else { return }
        let task = URLSession.shared.webSocketTask(with: url)
        scanTask = task
        task.resume()
        receiveLoop(task: task, onMessage: onUpdate)
    }

    func disconnect() {
        priceTask?.cancel(with: .goingAway, reason: nil)
        scanTask?.cancel(with: .goingAway, reason: nil)
        priceTask = nil
        scanTask = nil
        isConnected = false
    }

    private func receiveLoop(task: URLSessionWebSocketTask, onMessage: @escaping ([String: Any]) -> Void) {
        task.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        DispatchQueue.main.async { onMessage(json) }
                    }
                default: break
                }
                self?.receiveLoop(task: task, onMessage: onMessage)
            case .failure:
                DispatchQueue.main.async { self?.isConnected = false }
                // Reconnect after delay
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    self?.isConnected = false
                }
            }
        }
    }
}
