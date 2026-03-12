'use client';
import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import IndexBar from '@/components/IndexBar';

interface Filters {
  pe_min: number; pe_max: number;
  roe_min: number; roe_max: number;
  mcap_min: number; mcap_max: number;
  de_max: number;
  div_min: number;
}

interface FundResult {
  symbol: string;
  company_name: string;
  sector: string;
  ltp: number;
  pe_ratio: number;
  roe: number;
  market_cap_cr: number;
  debt_equity: number;
  dividend_yield: number;
  quality_score: number;
}

const DEFAULT_FILTERS: Filters = {
  pe_min: 0, pe_max: 100,
  roe_min: 0, roe_max: 100,
  mcap_min: 0, mcap_max: 500000,
  de_max: 5,
  div_min: 0,
};

// Mock data for demonstration — will be replaced by API when backend supports it
const MOCK_DATA: FundResult[] = [
  { symbol: 'TCS', company_name: 'Tata Consultancy Services', sector: 'IT', ltp: 3890.10, pe_ratio: 28.5, roe: 45.2, market_cap_cr: 1420000, debt_equity: 0.04, dividend_yield: 1.2, quality_score: 92 },
  { symbol: 'INFY', company_name: 'Infosys Ltd', sector: 'IT', ltp: 1542.80, pe_ratio: 24.1, roe: 31.8, market_cap_cr: 640000, debt_equity: 0.08, dividend_yield: 2.1, quality_score: 88 },
  { symbol: 'HDFCBANK', company_name: 'HDFC Bank Ltd', sector: 'Banking', ltp: 1672.35, pe_ratio: 19.2, roe: 16.4, market_cap_cr: 1280000, debt_equity: 0.0, dividend_yield: 1.0, quality_score: 85 },
  { symbol: 'RELIANCE', company_name: 'Reliance Industries', sector: 'Conglomerate', ltp: 2485.60, pe_ratio: 26.8, roe: 9.2, market_cap_cr: 1680000, debt_equity: 0.38, dividend_yield: 0.3, quality_score: 78 },
  { symbol: 'BAJFINANCE', company_name: 'Bajaj Finance Ltd', sector: 'NBFC', ltp: 6820.40, pe_ratio: 32.1, roe: 22.5, market_cap_cr: 420000, debt_equity: 3.2, dividend_yield: 0.4, quality_score: 74 },
  { symbol: 'LT', company_name: 'Larsen & Toubro', sector: 'Infrastructure', ltp: 3452.70, pe_ratio: 35.4, roe: 14.8, market_cap_cr: 480000, debt_equity: 1.1, dividend_yield: 0.8, quality_score: 72 },
  { symbol: 'SBIN', company_name: 'State Bank of India', sector: 'Banking', ltp: 625.30, pe_ratio: 9.8, roe: 17.2, market_cap_cr: 560000, debt_equity: 0.0, dividend_yield: 1.8, quality_score: 80 },
  { symbol: 'WIPRO', company_name: 'Wipro Ltd', sector: 'IT', ltp: 452.60, pe_ratio: 20.3, roe: 16.1, market_cap_cr: 236000, debt_equity: 0.18, dividend_yield: 0.2, quality_score: 70 },
];

function scoreColor(score: number): string {
  if (score >= 85) return 'var(--green)';
  if (score >= 70) return 'var(--amber)';
  return 'var(--red)';
}

export default function FundamentalsPage() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  const filtered = MOCK_DATA.filter(r =>
    r.pe_ratio >= filters.pe_min && r.pe_ratio <= filters.pe_max &&
    r.roe >= filters.roe_min && r.roe <= filters.roe_max &&
    r.market_cap_cr >= filters.mcap_min && r.market_cap_cr <= filters.mcap_max &&
    r.debt_equity <= filters.de_max &&
    r.dividend_yield >= filters.div_min
  ).sort((a, b) => b.quality_score - a.quality_score);

  const fmtPrice = (n: number) => '\u20B9' + n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  const fmtMcap = (n: number) => n >= 100000 ? `${(n / 100000).toFixed(1)}L Cr` : `${(n / 1000).toFixed(0)}K Cr`;

  const updateFilter = (key: keyof Filters, value: number) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px' }}>Fundamentals</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Filter stocks by PE, ROE, Market Cap &amp; more with quality scoring
            </p>
          </div>
          <button className="btn btn-ghost" style={{ fontSize: '13px', padding: '8px 14px' }}
            onClick={() => setFilters(DEFAULT_FILTERS)}>
            Reset Filters
          </button>
        </div>

        <IndexBar />

        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '20px', marginTop: '20px' }}>

          {/* Filter Sidebar */}
          <div className="card" style={{ height: 'fit-content' }}>
            <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '20px' }}>Filter Criteria</div>

            {/* PE Ratio */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                PE Ratio
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.pe_min} onChange={e => updateFilter('pe_min', Number(e.target.value))} />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.pe_max} onChange={e => updateFilter('pe_max', Number(e.target.value))} />
              </div>
            </div>

            {/* ROE */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ROE (%)
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.roe_min} onChange={e => updateFilter('roe_min', Number(e.target.value))} />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.roe_max} onChange={e => updateFilter('roe_max', Number(e.target.value))} />
              </div>
            </div>

            {/* Market Cap */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Market Cap (Cr)
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.mcap_min} onChange={e => updateFilter('mcap_min', Number(e.target.value))} />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input className="input-field" type="number" style={{ width: '80px', fontSize: '13px', padding: '6px 8px' }}
                  value={filters.mcap_max} onChange={e => updateFilter('mcap_max', Number(e.target.value))} />
              </div>
            </div>

            {/* Debt-to-Equity */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Max Debt/Equity
              </div>
              <input className="input-field" type="number" step="0.1" style={{ width: '100px', fontSize: '13px', padding: '6px 8px' }}
                value={filters.de_max} onChange={e => updateFilter('de_max', Number(e.target.value))} />
            </div>

            {/* Dividend Yield */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Min Dividend Yield (%)
              </div>
              <input className="input-field" type="number" step="0.1" style={{ width: '100px', fontSize: '13px', padding: '6px 8px' }}
                value={filters.div_min} onChange={e => updateFilter('div_min', Number(e.target.value))} />
            </div>
          </div>

          {/* Results Table */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontWeight: '700', fontSize: '15px', flex: 1 }}>
                Fundamental Analysis
                <span className="badge badge-accent" style={{ marginLeft: '8px' }}>{filtered.length} stocks</span>
              </div>
            </div>
            <div style={{ overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Sector</th>
                    <th style={{ textAlign: 'right' }}>LTP</th>
                    <th style={{ textAlign: 'right' }}>PE</th>
                    <th style={{ textAlign: 'right' }}>ROE %</th>
                    <th style={{ textAlign: 'right' }}>Market Cap</th>
                    <th style={{ textAlign: 'right' }}>D/E</th>
                    <th style={{ textAlign: 'right' }}>Div Yield</th>
                    <th style={{ textAlign: 'center' }}>Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                        No stocks match current filters. Try widening your criteria.
                      </td>
                    </tr>
                  ) : filtered.map(r => (
                    <tr key={r.symbol} onClick={() => window.location.href = `/chart?symbol=${r.symbol}`}>
                      <td><span style={{ fontWeight: '700', color: 'var(--accent)' }}>{r.symbol}</span></td>
                      <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{r.company_name}</td>
                      <td><span className="badge badge-accent" style={{ fontSize: '10px' }}>{r.sector}</span></td>
                      <td className="mono" style={{ textAlign: 'right', fontWeight: '600' }}>{fmtPrice(r.ltp)}</td>
                      <td className="mono" style={{ textAlign: 'right', color: r.pe_ratio < 20 ? 'var(--green)' : r.pe_ratio > 40 ? 'var(--red)' : 'var(--text-primary)' }}>
                        {r.pe_ratio.toFixed(1)}
                      </td>
                      <td className="mono" style={{ textAlign: 'right', color: r.roe > 20 ? 'var(--green)' : 'var(--text-secondary)' }}>
                        {r.roe.toFixed(1)}%
                      </td>
                      <td className="mono" style={{ textAlign: 'right', fontSize: '12px' }}>{fmtMcap(r.market_cap_cr)}</td>
                      <td className="mono" style={{ textAlign: 'right', color: r.debt_equity > 1 ? 'var(--amber)' : 'var(--text-secondary)' }}>
                        {r.debt_equity.toFixed(2)}
                      </td>
                      <td className="mono" style={{ textAlign: 'right' }}>{r.dividend_yield.toFixed(1)}%</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          width: '40px', height: '28px', borderRadius: '6px',
                          background: scoreColor(r.quality_score) === 'var(--green)' ? 'var(--green-dim)' :
                            scoreColor(r.quality_score) === 'var(--amber)' ? 'var(--amber-dim)' : 'var(--red-dim)',
                          color: scoreColor(r.quality_score),
                          fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: '700',
                        }}>
                          {r.quality_score}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
