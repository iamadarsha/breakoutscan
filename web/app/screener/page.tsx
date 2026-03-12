'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import IndexBar from '@/components/IndexBar';
import api, { PrebuiltScan, ScanResult } from '@/lib/api';

const CATEGORY_COLORS: Record<string, string> = {
  Pattern: 'badge-amber', Breakout: 'badge-accent', RSI: 'badge-green',
  EMA: 'badge-amber', MACD: 'badge-amber', Volume: 'badge-red',
  Trend: 'badge-accent', Volatility: 'badge-accent', Intraday: 'badge-green',
  VWAP: 'badge-green', Momentum: 'badge-accent',
};

export default function ScreenerPage() {
  const [prebuilt, setPrebuilt] = useState<PrebuiltScan[]>([]);
  const [results, setResults] = useState<ScanResult[]>([]);
  const [activeScan, setActiveScan] = useState<string>('');
  const [scanName, setScanName] = useState('');
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    api.getPrebuiltScans().then(setPrebuilt).catch(console.warn);
  }, []);

  const runScan = async (scan: PrebuiltScan) => {
    setLoading(true);
    setActiveScan(scan.id);
    setScanName(scan.name);
    setResults([]);
    try {
      const resp = await api.runPrebuiltScan(scan.id);
      setResults(resp.results || []);
      setDuration(resp.duration_ms);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fmtPrice = (n: number) => '\u20B9' + n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  const fmtVol = (n: number) => n >= 1e7 ? `${(n/1e7).toFixed(1)}Cr` : n >= 1e5 ? `${(n/1e5).toFixed(1)}L` : `${(n/1000).toFixed(0)}K`;

  const filtered = results.filter(r =>
    !filter || r.symbol.includes(filter.toUpperCase()) || (r.company_name || '').toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px' }}>Stock Screener</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {prebuilt.length} pre-built scans &bull; Click any scan to run &bull; Real-time results
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="live-dot" />
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>NSE Universe &bull; 2000+ stocks</span>
          </div>
        </div>

        <IndexBar />

        {/* Scan Cards Grid */}
        <div style={{ marginTop: '20px', marginBottom: '24px' }}>
          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Pre-built Scanners
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
            {prebuilt.map((scan) => (
              <div
                key={scan.id}
                onClick={() => runScan(scan)}
                className="card"
                style={{
                  padding: '14px 16px',
                  cursor: 'pointer',
                  border: activeScan === scan.id ? '1px solid var(--accent)' : '1px solid var(--border)',
                  background: activeScan === scan.id ? 'rgba(124,92,252,0.08)' : 'var(--bg-card)',
                  transition: 'all 200ms',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {activeScan === scan.id && (
                  <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: 'var(--accent)' }} />
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ fontSize: '18px' }}>{scan.icon}</span>
                  <span style={{ fontWeight: '700', fontSize: '13px', flex: 1, lineHeight: 1.3 }}>{scan.name}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: 1.4 }}>
                  {scan.description.length > 80 ? scan.description.slice(0, 80) + '...' : scan.description}
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <span className={`badge ${CATEGORY_COLORS[scan.category] || 'badge-accent'}`}>{scan.category}</span>
                  <span className="badge badge-accent" style={{ opacity: 0.7 }}>{scan.timeframe}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Results Section */}
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ fontWeight: '700', fontSize: '15px', flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
              {scanName ? (
                <>
                  {scanName}
                  {results.length > 0 && (
                    <span className="badge badge-green">{results.length} results</span>
                  )}
                  {duration > 0 && (
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>in {duration}ms</span>
                  )}
                </>
              ) : (
                <span style={{ color: 'var(--text-secondary)' }}>Click a scan above to run it</span>
              )}
            </div>
            {results.length > 0 && (
              <input
                className="input-field"
                style={{ width: '200px' }}
                placeholder="Filter results..."
                value={filter}
                onChange={e => setFilter(e.target.value)}
              />
            )}
          </div>
          <div style={{ overflow: 'auto', maxHeight: '500px' }}>
            {loading ? (
              <div style={{ padding: '60px', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', marginBottom: '16px', animation: 'pulse-dot 1s infinite' }}>&#x1F50D;</div>
                <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--accent)' }}>Scanning 2000+ NSE stocks...</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>Using Redis pipeline batch evaluation</div>
              </div>
            ) : !scanName ? (
              <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>&#x1F4CA;</div>
                <div style={{ fontSize: '15px', fontWeight: '600' }}>Select a scanner above</div>
                <div style={{ fontSize: '13px', marginTop: '6px' }}>Choose any of the {prebuilt.length} pre-built scans to find breakout stocks</div>
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                &#x1F50D; No stocks matched this scan right now.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}>#</th>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th style={{ textAlign: 'right' }}>LTP</th>
                    <th style={{ textAlign: 'right' }}>Change %</th>
                    <th style={{ textAlign: 'right' }}>Volume</th>
                    <th style={{ textAlign: 'right' }}>RSI(14)</th>
                    <th>EMA Status</th>
                    <th>Signals</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => (
                    <tr key={i} onClick={() => window.location.href=`/chart?symbol=${r.symbol}`}>
                      <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{i + 1}</td>
                      <td>
                        <div style={{ fontWeight: '700', color: 'var(--accent)' }}>{r.symbol}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{r.sector || 'NSE'}</div>
                      </td>
                      <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{r.company_name || '\u2014'}</td>
                      <td className="mono" style={{ textAlign: 'right', fontWeight: '600' }}>{fmtPrice(r.ltp)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <span className={r.change_pct >= 0 ? 'price-change-pos' : 'price-change-neg'}>
                          {r.change_pct >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(r.change_pct).toFixed(2)}%
                        </span>
                      </td>
                      <td className="mono" style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-secondary)' }}>{fmtVol(r.volume)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {r.rsi_14 != null && (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '3px' }}>
                            <span className="mono" style={{ fontSize: '13px', color: r.rsi_14 > 65 ? 'var(--amber)' : r.rsi_14 < 35 ? 'var(--green)' : 'var(--text-secondary)' }}>
                              {r.rsi_14.toFixed(1)}
                            </span>
                            <div className="rsi-bar-track" style={{ width: '50px' }}>
                              <div className="rsi-bar-fill" style={{
                                width: `${Math.min(100, r.rsi_14)}%`,
                                background: r.rsi_14 > 65 ? 'var(--amber)' : r.rsi_14 < 35 ? 'var(--green)' : 'var(--accent)',
                              }} />
                            </div>
                          </div>
                        )}
                      </td>
                      <td><span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{r.ema_status || '\u2014'}</span></td>
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {r.matched_conditions?.slice(0, 3).map((c, j) => (
                            <span key={j} className="badge badge-green" style={{ fontSize: '10px' }}>{'\u2713'} {c.length > 12 ? c.slice(0, 12) + '..' : c}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
