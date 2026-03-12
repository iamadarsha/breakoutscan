'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';

interface AIPick {
  symbol: string;
  company_name: string;
  action: string;
  confidence: number;
  target_pct: number;
  stop_loss_pct: number;
  reasoning: string;
  tags: string[];
}

interface AISuggestions {
  suggestions: {
    intraday: AIPick[];
    weekly: AIPick[];
    monthly: AIPick[];
  } | null;
  generated_at: string;
  generation_time_ms: number;
  news_count: number;
  model: string;
  news_headlines: string[];
  error?: string;
}

type TimeFrame = 'intraday' | 'weekly' | 'monthly';

const TF_LABELS: Record<TimeFrame, { label: string; icon: string; desc: string }> = {
  intraday: { label: 'Intraday', icon: '\u26A1', desc: 'Same-day trades' },
  weekly: { label: 'Weekly', icon: '\uD83D\uDCC8', desc: '1\u20135 day swings' },
  monthly: { label: 'Monthly', icon: '\uD83C\uDFAF', desc: '2\u20134 week positions' },
};

export default function AIPicksPage() {
  const [data, setData] = useState<AISuggestions | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTF, setActiveTF] = useState<TimeFrame>('intraday');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const resp = await api.getAISuggestions();
      setData(resp);
      setError('');
    } catch (e: any) {
      setError('Failed to load AI suggestions. Make sure Gemini API is configured.');
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    try {
      const resp = await api.refreshAISuggestions();
      setData(resp);
      setError('');
    } catch (e: any) {
      setError('Refresh failed. Try again later.');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const picks = data?.suggestions?.[activeTF] || [];

  const fmtTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  };

  const confidenceColor = (c: number) =>
    c >= 80 ? 'var(--green)' : c >= 65 ? 'var(--amber)' : 'var(--text-secondary)';

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px' }}>{'\uD83E\uDDE0'}</span> AI Picks
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Powered by Gemini 2.5 Flash &bull; News-driven analysis &bull; Updated every 6 hours
            </p>
          </div>
          <button
            onClick={refresh}
            disabled={refreshing}
            style={{
              padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--accent)',
              background: refreshing ? 'var(--bg-card)' : 'rgba(124,92,252,0.12)',
              color: 'var(--accent)', fontWeight: '600', fontSize: '13px', cursor: refreshing ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}
          >
            {refreshing ? '\u23F3 Generating...' : '\uD83D\uDD04 Refresh'}
          </button>
        </div>

        {/* Timeframe Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
          {(Object.keys(TF_LABELS) as TimeFrame[]).map(tf => {
            const active = tf === activeTF;
            const { label, icon, desc } = TF_LABELS[tf];
            const count = data?.suggestions?.[tf]?.length || 0;
            return (
              <div
                key={tf}
                onClick={() => setActiveTF(tf)}
                style={{
                  flex: 1, padding: '14px 16px', borderRadius: '12px', cursor: 'pointer',
                  border: active ? '1px solid var(--accent)' : '1px solid var(--border)',
                  background: active ? 'rgba(124,92,252,0.08)' : 'var(--bg-card)',
                  transition: 'all 200ms',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '18px' }}>{icon}</span>
                  <span style={{ fontWeight: '700', fontSize: '14px' }}>{label}</span>
                  {count > 0 && (
                    <span className="badge badge-accent" style={{ marginLeft: 'auto' }}>{count} picks</span>
                  )}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{desc}</div>
              </div>
            );
          })}
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="card" style={{ padding: '80px', textAlign: 'center' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px', animation: 'pulse-dot 1.5s infinite' }}>{'\uD83E\uDDE0'}</div>
            <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--accent)' }}>AI is analyzing market data...</div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>
              Gathering news, scanning technicals, generating picks
            </div>
          </div>
        ) : error ? (
          <div className="card" style={{ padding: '60px', textAlign: 'center' }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>{'\u26A0\uFE0F'}</div>
            <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--amber)' }}>{error}</div>
            <button onClick={load} style={{
              marginTop: '16px', padding: '8px 20px', borderRadius: '8px',
              background: 'var(--accent)', color: '#000', fontWeight: '600', border: 'none', cursor: 'pointer',
            }}>Retry</button>
          </div>
        ) : (
          <>
            {/* Meta info bar */}
            {data && (
              <div style={{
                display: 'flex', gap: '16px', marginBottom: '16px', padding: '10px 16px',
                borderRadius: '8px', background: 'var(--bg-card)', border: '1px solid var(--border)',
                fontSize: '12px', color: 'var(--text-secondary)', flexWrap: 'wrap', alignItems: 'center',
              }}>
                <span>{'\uD83D\uDD52'} Generated: {fmtTime(data.generated_at)}</span>
                <span>{'\u23F1\uFE0F'} {data.generation_time_ms}ms</span>
                <span>{'\uD83D\uDCF0'} {data.news_count} news articles analyzed</span>
                <span>{'\uD83E\uDD16'} {data.model}</span>
              </div>
            )}

            {/* Picks Grid */}
            {picks.length === 0 ? (
              <div className="card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>{'\uD83D\uDCCA'}</div>
                <div style={{ fontSize: '15px', fontWeight: '600' }}>No picks available for {TF_LABELS[activeTF].label}</div>
                <div style={{ fontSize: '13px', marginTop: '6px' }}>Click Refresh to generate fresh AI suggestions</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '14px' }}>
                {picks.map((pick, i) => (
                  <div key={i} className="card" style={{ padding: '18px', position: 'relative', overflow: 'hidden' }}>
                    {/* Top accent bar */}
                    <div style={{
                      position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
                      background: pick.action === 'BUY'
                        ? 'linear-gradient(90deg, var(--green), var(--accent))'
                        : 'linear-gradient(90deg, var(--red), var(--amber))',
                    }} />

                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: '800', fontSize: '16px', color: 'var(--accent)' }}>{pick.symbol}</span>
                          <span className={`badge ${pick.action === 'BUY' ? 'badge-green' : 'badge-red'}`}>
                            {pick.action}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                          {pick.company_name}
                        </div>
                      </div>
                      {/* Confidence meter */}
                      <div style={{ textAlign: 'center' }}>
                        <div style={{
                          fontSize: '20px', fontWeight: '800', color: confidenceColor(pick.confidence),
                          lineHeight: 1,
                        }}>
                          {pick.confidence}%
                        </div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>confidence</div>
                      </div>
                    </div>

                    {/* Target / Stop Loss */}
                    <div style={{
                      display: 'flex', gap: '12px', marginBottom: '12px', padding: '10px 12px',
                      background: 'var(--bg-primary)', borderRadius: '8px',
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Target
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--green)' }}>
                          +{pick.target_pct}%
                        </div>
                      </div>
                      <div style={{ width: '1px', background: 'var(--border)' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Stop Loss
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--red)' }}>
                          -{pick.stop_loss_pct}%
                        </div>
                      </div>
                      <div style={{ width: '1px', background: 'var(--border)' }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Risk:Reward
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--accent)' }}>
                          1:{(pick.target_pct / pick.stop_loss_pct).toFixed(1)}
                        </div>
                      </div>
                    </div>

                    {/* Reasoning */}
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '10px' }}>
                      {pick.reasoning}
                    </div>

                    {/* Tags */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {pick.tags.map((tag, j) => (
                        <span key={j} className="badge badge-accent" style={{ fontSize: '11px' }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* News Headlines */}
            {data?.news_headlines && data.news_headlines.length > 0 && (
              <div className="card" style={{ marginTop: '20px', padding: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {'\uD83D\uDCF0'} News Sources Analyzed
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {data.news_headlines.map((h, i) => (
                    <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '4px 0', borderBottom: i < data.news_headlines.length - 1 ? '1px solid var(--border)' : 'none' }}>
                      {h}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div style={{
              marginTop: '20px', padding: '12px 16px', borderRadius: '8px',
              background: 'rgba(255,183,0,0.06)', border: '1px solid rgba(255,183,0,0.2)',
              fontSize: '11px', color: 'var(--amber)', lineHeight: 1.5,
            }}>
              {'\u26A0\uFE0F'} <strong>Disclaimer:</strong> AI-generated suggestions are for educational purposes only.
              Not financial advice. Always do your own research before trading.
              Past performance does not guarantee future results.
            </div>
          </>
        )}
      </main>
    </div>
  );
}
