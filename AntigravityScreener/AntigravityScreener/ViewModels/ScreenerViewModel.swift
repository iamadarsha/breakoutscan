import Foundation

@Observable
class ScreenerViewModel {
    var scans: [PrebuiltScan] = []
    var results: [ScanResult] = []
    var activeScanId: String?
    var activeScanName: String?
    var durationMs = 0
    var isLoading = false
    var isScanning = false

    func loadScans() async {
        isLoading = true
        do {
            scans = try await APIClient.shared.getPrebuiltScans()
        } catch {
            print("Failed to load scans: \(error)")
        }
        isLoading = false
    }

    func runScan(_ scan: PrebuiltScan) async {
        isScanning = true
        activeScanId = scan.id
        activeScanName = scan.name
        results = []
        do {
            let resp = try await APIClient.shared.runPrebuiltScan(id: scan.id)
            results = resp.results
            durationMs = resp.durationMs
        } catch {
            print("Scan failed: \(error)")
        }
        isScanning = false
    }
}
