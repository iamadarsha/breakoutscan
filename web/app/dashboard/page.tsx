'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import IndexBar from '@/components/IndexBar';
import api, { ScanResult, WatchlistItem } from '@/lib/api';

interface ScanHit {
  symbol: string;
  scan_name: string;
  scan_id: string;
  ltp: number;
  change_pct: number;
  volume: number;
  rsi_14?: number;
  triggered_at: string;
}

export default function Dashboard() {
  const [scanHits, setScanHits] = useState<ScanHit[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const [hits, wl] = await Promise.allSettled([
        api.getLatestResults(),
        api.getWatchlist(),
      ]);
      if (hits.status === 'fulfilled') setScanHits(hits.value.results || []);
      if (wl.status === 'fulfilled') setWatchlist(wl.value || []);
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const fmtPrice = (n: number) => '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtVol = (n: number) => n >= 1e7 ? `${(n/1e7).toFixed(1)}Cr` : n >= 1e5 ? `${(n/1e5).toFixed(1)}L` : n.toLocaleString();

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px' }}>Dashboard</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <span className="live-dot" />
              <span>Live NSE data • {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} IST</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-ghost" style={{ fontSize: '13px', padding: '8px 14px' }}>⚙️ Settings</button>
            <button className="btn btn-primary" style={{ fontSize: '13px', padding: '8px 16px' }} onClick={() => window.location.href='/screener'}>
              🔍 Run Scan
            </button>
          </div>
        </div>

        {/* Index Bar */}
        <IndexBar />

        {/* Stats Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', margin: '20px 0' }}>
          {[
            { label: 'Scan Hits Today', value: scanHits.length, suffix: 'stocks', color: 'var(--accent)', icon: '🎯' },
            { label: 'Watchlist', value: watchlist.length, suffix: 'stocks', color: 'var(--green)', icon: '⭐' },
            { label: 'Active Alerts', value: 3, suffix: 'active', color: 'var(--amber)', icon: '🔔' },
            { label: 'Market Breadth', value: '62%', suffix: 'Advances', color: 'var(--green)', icon: '📊' },
          ].map((stat) => (
            <div key={stat.label} className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                <span style={{ fontSize: '16px' }}>{stat.icon}</span>
                <span className="metric-label" style={{ margin: 0 }}>{stat.label}</span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '28px', fontWeight: '700', color: stat.color }}>
                {stat.value}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{stat.suffix}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px' }}>

          {/* Scan Hits Table */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontWeight: '700', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🎯 Live Scan Hits
                <span className="badge badge-green">{scanHits.length} stocks</span>
              </div>
              <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={() => window.location.href='/screener'}>
                View All →
              </button>
            </div>
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Scan</th>
                    <th style={{ textAlign: 'right' }}>LTP</th>
                    <th style={{ textAlign: 'right' }}>Change</th>
                    <th style={{ textAlign: 'right' }}>Volume</th>
                    <th style={{ textAlign: 'right' }}>RSI</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 6 }).map((_, j) => (
                          <td key={j}><div className="skeleton" style={{ height: 16, width: '80%' }} /></td>
                        ))}
                      </tr>
                    ))
                  ) : scanHits.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '40px', fontSize: '14px' }}>
                        No scan hits yet. Market data loading...
                      </td>
                    </tr>
                  ) : (
                    scanHits.map((hit, i) => (
                      <tr key={i} className="scan-hit" onClick={() => window.location.href=`/chart?symbol=${hit.symbol}`}>
                        <td>
                          <div style={{ fontWeight: '700', fontSize: '14px' }}>{hit.symbol}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{hit.scan_name}</div>
                        </td>
                        <td><span className="badge badge-amber">{hit.scan_name.split(' ')[0]}</span></td>
                        <td className="mono" style={{ textAlign: 'right', fontWeight: '600' }}>{fmtPrice(hit.ltp)}</td>
                        <td style={{ textAlign: 'right' }}>
                          <span className={hit.change_pct >= 0 ? 'price-change-pos' : 'price-change-neg'}>
                            {hit.change_pct >= 0 ? '▲' : '▼'} {Math.abs(hit.change_pct).toFixed(2)}%
                          </span>
                        </td>
                        <td className="mono" style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-secondary)' }}>{fmtVol(hit.volume)}</td>
                        <td style={{ textAlign: 'right' }}>
                          {hit.rsi_14 != null && (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: hit.rsi_14 > 70 ? 'var(--amber)' : hit.rsi_14 < 30 ? 'var(--green)' : 'var(--text-secondary)' }}>
                              {hit.rsi_14.toFixed(1)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Watchlist Panel */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontWeight: '700', fontSize: '15px' }}>⭐ Watchlist</div>
              <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={() => window.location.href='/watchlist'}>
                Manage →
              </button>
            </div>
            <div style={{ padding: '8px' }}>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} style={{ padding: '12px', marginBottom: '4px' }}>
                    <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: '8px' }} />
                    <div className="skeleton" style={{ height: 12, width: '40%' }} />
                  </div>
                ))
              ) : watchlist.map((item) => (
                <div key={item.symbol} className="scan-row" style={{ marginBottom: '6px' }} onClick={() => window.location.href=`/chart?symbol=${item.symbol}`}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '3px' }}>
                      {item.symbol}
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '400', marginLeft: '6px' }}>{item.sector}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      RSI {item.rsi_14?.toFixed(1)} · {item.ema20_status}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="mono" style={{ fontSize: '15px', fontWeight: '600', marginBottom: '3px' }}>
                      ₹{item.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </div>
                    <div className={item.change_pct >= 0 ? 'price-change-pos' : 'price-change-neg'} style={{ fontSize: '13px' }}>
                      {item.change_pct >= 0 ? '▲' : '▼'} {Math.abs(item.change_pct).toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
