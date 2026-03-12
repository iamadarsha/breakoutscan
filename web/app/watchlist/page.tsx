'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import IndexBar from '@/components/IndexBar';
import api, { WatchlistItem } from '@/lib/api';

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [addSymbol, setAddSymbol] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const load = async () => {
    try { setItems(await api.getWatchlist()); } catch (e) { console.warn(e); }
    setLoading(false);
  };

  useEffect(() => { load(); const i = setInterval(load, 8000); return () => clearInterval(i); }, []);

  const handleSearch = async (q: string) => {
    setAddSymbol(q);
    if (q.length >= 2) {
      try { setSearchResults(await api.searchStocks(q)); } catch { setSearchResults([]); }
    } else { setSearchResults([]); }
  };

  const handleAdd = async (symbol: string) => {
    await api.addToWatchlist(symbol);
    setAddSymbol(''); setSearchResults([]);
    load();
  };

  const handleRemove = async (symbol: string) => {
    await api.removeWatchlist(symbol);
    load();
  };

  const fmtPrice = (n: number) => '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 2 });

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px' }}>Watchlist</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{items.length} stocks • Live prices with RSI & EMA signals</p>
          </div>
        </div>

        <IndexBar />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px', marginTop: '20px' }}>
          {/* Main Table */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', fontWeight: '700', fontSize: '15px' }}>
              ⭐ Your Watchlist
              <span className="badge badge-accent" style={{ marginLeft: '8px' }}>{items.length}</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Company</th>
                  <th style={{ textAlign: 'right' }}>LTP</th>
                  <th style={{ textAlign: 'right' }}>Change</th>
                  <th style={{ textAlign: 'right' }}>Volume</th>
                  <th style={{ textAlign: 'right' }}>RSI(14)</th>
                  <th>EMA Status</th>
                  <th>Sector</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>{Array.from({ length: 9 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 14, width: '80%' }} /></td>)}</tr>
                  ))
                ) : items.length === 0 ? (
                  <tr><td colSpan={9} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                    Your watchlist is empty. Add stocks using the panel →
                  </td></tr>
                ) : items.map(item => (
                  <tr key={item.symbol}>
                    <td>
                      <span style={{ fontWeight: '700', cursor: 'pointer', color: 'var(--accent)' }}
                        onClick={() => window.location.href=`/chart?symbol=${item.symbol}`}>
                        {item.symbol}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{item.company_name || '—'}</td>
                    <td className="mono" style={{ textAlign: 'right', fontWeight: '600' }}>{fmtPrice(item.ltp)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className={item.change_pct >= 0 ? 'price-change-pos' : 'price-change-neg'}>
                        {item.change_pct >= 0 ? '▲' : '▼'} {Math.abs(item.change_pct).toFixed(2)}%
                      </span>
                    </td>
                    <td className="mono" style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {item.volume ? (item.volume >= 1e7 ? `${(item.volume/1e7).toFixed(1)}Cr` : `${(item.volume/1e5).toFixed(1)}L`) : '—'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {item.rsi_14 != null && (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                          <span className="mono" style={{ fontSize: '13px', color: item.rsi_14 > 65 ? 'var(--amber)' : item.rsi_14 < 35 ? 'var(--green)' : 'var(--text-primary)' }}>
                            {item.rsi_14.toFixed(1)}
                          </span>
                          <div className="rsi-bar-track" style={{ width: '60px' }}>
                            <div className="rsi-bar-fill" style={{
                              width: `${item.rsi_14}%`,
                              background: item.rsi_14 > 65 ? 'var(--amber)' : item.rsi_14 < 35 ? 'var(--green)' : 'var(--accent)',
                            }} />
                          </div>
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${item.ema20_status?.includes('Above') ? 'badge-green' : 'badge-red'}`} style={{ fontSize: '10px' }}>
                        {item.ema20_status || '—'}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{item.sector || '—'}</td>
                    <td>
                      <button onClick={() => handleRemove(item.symbol)} style={{ color: 'var(--red)', fontSize: '16px', lineHeight: 1, background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Add Stock Panel */}
          <div className="card" style={{ height: 'fit-content' }}>
            <div style={{ fontWeight: '700', fontSize: '15px', marginBottom: '16px' }}>➕ Add to Watchlist</div>
            <div style={{ position: 'relative' }}>
              <input
                className="input-field"
                placeholder="Search symbol or name..."
                value={addSymbol}
                onChange={e => handleSearch(e.target.value)}
              />
              {searchResults.length > 0 && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: '8px', marginTop: '4px', overflow: 'hidden',
                }}>
                  {searchResults.map((r) => (
                    <div
                      key={r.symbol}
                      onClick={() => handleAdd(r.symbol)}
                      style={{ padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border)', transition: 'background 150ms' }}
                      onMouseEnter={e => (e.currentTarget as any).style.background = 'var(--bg-card-hover)'}
                      onMouseLeave={e => (e.currentTarget as any).style.background = ''}
                    >
                      <div style={{ fontWeight: '700', fontSize: '14px' }}>{r.symbol}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{r.company_name}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ marginTop: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Popular stocks
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {['RELIANCE', 'HDFCBANK', 'TCS', 'INFY', 'TATAMOTORS', 'SBIN', 'BAJFINANCE', 'LT', 'AXISBANK', 'WIPRO'].map(s => (
                  <button key={s} className="badge badge-accent" style={{ cursor: 'pointer' }} onClick={() => handleAdd(s)}>
                    + {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
