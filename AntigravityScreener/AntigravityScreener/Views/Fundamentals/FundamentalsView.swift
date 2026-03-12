import SwiftUI

struct FundamentalsView: View {
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 12) {
                        Text("📊")
                            .font(.system(size: 48))
                        Text("Fundamentals")
                            .font(.system(size: 20, weight: .bold))
                        Text("Filter stocks by PE, ROE, Market Cap & more")
                            .font(.system(size: 13))
                            .foregroundColor(E8.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(.vertical, 40)

                    // Quick stats
                    VStack(alignment: .leading, spacing: 12) {
                        Text("TOP QUALITY STOCKS")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(E8.textSecondary)
                            .tracking(0.5)

                        ForEach(fundamentalStocks, id: \.symbol) { stock in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(stock.symbol)
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(E8.accent)
                                    Text(stock.company)
                                        .font(.system(size: 11))
                                        .foregroundColor(E8.textSecondary)
                                }
                                Spacer()
                                VStack(alignment: .trailing, spacing: 2) {
                                    Text("PE: \(String(format: "%.1f", stock.pe))")
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(E8.textSecondary)
                                    Text("ROE: \(String(format: "%.1f%%", stock.roe))")
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(stock.roe > 20 ? E8.green : E8.amber)
                                }
                                BadgeView(text: stock.quality, color: stock.quality == "A+" ? E8.green : E8.amber)
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                            Divider().background(E8.border)
                        }
                    }
                    .cardStyle()
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(E8.bgPrimary)
            .navigationTitle("Fundamentals")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(E8.bgCard, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
    }
}

private struct FundStock {
    let symbol: String
    let company: String
    let pe: Double
    let roe: Double
    let quality: String
}

private let fundamentalStocks = [
    FundStock(symbol: "BAJFINANCE", company: "Bajaj Finance Ltd", pe: 32.1, roe: 22.5, quality: "A+"),
    FundStock(symbol: "LT", company: "Larsen & Toubro", pe: 35.4, roe: 14.8, quality: "A"),
    FundStock(symbol: "WIPRO", company: "Wipro Ltd", pe: 20.3, roe: 16.1, quality: "A"),
    FundStock(symbol: "TCS", company: "TCS Ltd", pe: 28.5, roe: 45.2, quality: "A+"),
    FundStock(symbol: "HDFCBANK", company: "HDFC Bank Ltd", pe: 19.8, roe: 17.3, quality: "A+"),
]
