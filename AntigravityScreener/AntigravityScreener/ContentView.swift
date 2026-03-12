import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var chartSymbol = "RELIANCE"

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(onSelectSymbol: { sym in
                chartSymbol = sym
                selectedTab = 2
            })
            .tabItem {
                Image(systemName: "house.fill")
                Text("Dashboard")
            }
            .tag(0)

            ScreenerView()
                .tabItem {
                    Image(systemName: "magnifyingglass")
                    Text("Screener")
                }
                .tag(1)

            ChartView()
                .tabItem {
                    Image(systemName: "chart.xyaxis.line")
                    Text("Charts")
                }
                .tag(2)

            WatchlistView()
                .tabItem {
                    Image(systemName: "star.fill")
                    Text("Watchlist")
                }
                .tag(3)

            AlertsView()
                .tabItem {
                    Image(systemName: "bell.fill")
                    Text("Alerts")
                }
                .tag(4)

            FundamentalsView()
                .tabItem {
                    Image(systemName: "chart.bar.fill")
                    Text("More")
                }
                .tag(5)
        }
        .tint(E8.accent)
    }
}
