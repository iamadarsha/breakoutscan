'use client';
import { useRouter } from 'next/navigation';

const FEATURES = [
  { icon: '🔍', title: '12 Pre-built Scans', desc: 'Bullish Harami, EMA Crossover, RSI Bounce, VWAP Reclaim and more' },
  { icon: '📈', title: 'Live Charts', desc: 'Candlestick charts with EMA, RSI, MACD overlays in real-time' },
  { icon: '⚡', title: 'Sub-2s Screener', desc: 'Redis pipeline batch evaluation across 2000+ NSE stocks' },
  { icon: '🔔', title: 'Smart Alerts', desc: 'Push, Telegram & Email alerts when scan conditions trigger' },
  { icon: '⭐', title: 'Watchlist', desc: 'Track your favourite stocks with live prices, RSI & EMA signals' },
  { icon: '📊', title: 'Fundamentals', desc: 'Filter by PE, ROE, Market Cap with quality scoring' },
];

const TRENDING = [
  { symbol: 'RELIANCE', ltp: 2485.60, change: 1.24 },
  { symbol: 'HDFCBANK', ltp: 1672.35, change: -0.42 },
  { symbol: 'TCS', ltp: 3890.10, change: 0.87 },
  { symbol: 'INFY', ltp: 1542.80, change: 1.56 },
  { symbol: 'TATAMOTORS', ltp: 745.20, change: 2.31 },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div style={{ background: 'var(--bg-primary)', minHeight: '100vh', color: 'var(--text-primary)' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 40px', borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 36, height: 36, borderRadius: '10px',
            background: 'linear-gradient(135deg, #7C5CFC, #5A3ED9)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '18px', fontWeight: '800', color: '#fff',
          }}>B</div>
          <span style={{ fontSize: '18px', fontWeight: '800', letterSpacing: '-0.3px' }}>BreakoutScan</span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-ghost" onClick={() => router.push('/screener')}>Screener</button>
          <button className="btn btn-primary" onClick={() => router.push('/dashboard')}>Open Dashboard</button>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ textAlign: 'center', padding: '80px 20px 40px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <span className="live-dot" />
          <span style={{ fontSize: '13px', color: 'var(--green)', fontWeight: '600' }}>Live NSE + BSE Data</span>
        </div>
        <h1 style={{
          fontSize: '48px', fontWeight: '800', lineHeight: 1.15, marginBottom: '20px',
          background: 'linear-gradient(135deg, #EEEEF5, #7C5CFC)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          maxWidth: '700px', margin: '0 auto 20px',
        }}>
          India&apos;s Most Powerful Stock Screener
        </h1>
        <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '520px', margin: '0 auto 32px', lineHeight: 1.6 }}>
          12 pre-built scans, real-time charts, smart alerts &mdash; all running sub-2-second on 2000+ NSE stocks
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button className="btn btn-primary" style={{ fontSize: '16px', padding: '14px 32px' }}
            onClick={() => router.push('/dashboard')}>
            Open Dashboard
          </button>
          <button className="btn btn-outline" style={{ fontSize: '16px', padding: '14px 32px' }}
            onClick={() => router.push('/screener')}>
            Try Screener
          </button>
        </div>
      </section>

      {/* Stats */}
      <section style={{ display: 'flex', justifyContent: 'center', gap: '32px', padding: '20px', flexWrap: 'wrap' }}>
        {[
          { value: '2000+', label: 'NSE Stocks' },
          { value: '12', label: 'Pre-built Scans' },
          { value: '<2s', label: 'Scan Speed' },
          { value: '24/7', label: 'Alert Monitoring' },
        ].map(s => (
          <div key={s.label} style={{ textAlign: 'center', minWidth: '120px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: '800', color: 'var(--accent)' }}>{s.value}</div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>{s.label}</div>
          </div>
        ))}
      </section>

      {/* Trending Stocks Table */}
      <section style={{ maxWidth: '600px', margin: '40px auto', padding: '0 20px' }}>
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', fontWeight: '700', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            Trending Stocks <span className="badge badge-green">Live</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th style={{ textAlign: 'right' }}>LTP</th>
                <th style={{ textAlign: 'right' }}>Change</th>
              </tr>
            </thead>
            <tbody>
              {TRENDING.map(s => (
                <tr key={s.symbol} onClick={() => router.push(`/chart?symbol=${s.symbol}`)} style={{ cursor: 'pointer' }}>
                  <td style={{ fontWeight: '700' }}>{s.symbol}</td>
                  <td className="mono" style={{ textAlign: 'right' }}>
                    &#x20B9;{s.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className={s.change >= 0 ? 'price-change-pos' : 'price-change-neg'}>
                      {s.change >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(s.change).toFixed(2)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Features Grid */}
      <section style={{ maxWidth: '900px', margin: '40px auto 60px', padding: '0 20px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: '800', textAlign: 'center', marginBottom: '32px' }}>
          Everything you need to find breakout stocks
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
          {FEATURES.map(f => (
            <div key={f.title} className="card">
              <div style={{ fontSize: '24px', marginBottom: '10px' }}>{f.icon}</div>
              <div style={{ fontWeight: '700', fontSize: '15px', marginBottom: '6px' }}>{f.title}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '24px 40px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
        BreakoutScan &mdash; Real-time NSE & BSE Stock Screener
      </footer>
    </div>
  );
}
