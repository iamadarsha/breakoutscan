'use client';
import { useEffect, useRef, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import api, { OHLCVBar } from '@/lib/api';

const TIMEFRAMES = ['1min', '5min', '15min', '30min', '1hr', 'daily'];
const DEFAULT_SYMBOLS = ['RELIANCE', 'HDFCBANK', 'TATAMOTORS', 'WIPRO', 'ICICIBANK', 'TCS', 'INFY'];

function ChartContent() {
  const params = useSearchParams();
  const [symbol, setSymbol] = useState(params.get('symbol') || 'RELIANCE');
  const [tf, setTf] = useState('15min');
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [price, setPrice] = useState<any>(null);
  const [search, setSearch] = useState('');
  const [indicators, setIndicators] = useState({ rsi: true, ema: true, volume: true });
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const load = async () => {
      const [ohlcv, ltp] = await Promise.allSettled([
        api.getOHLCV(symbol, tf, 200),
        api.getPrice(symbol),
      ]);
      if (ohlcv.status === 'fulfilled') setBars(ohlcv.value.bars || []);
      if (ltp.status === 'fulfilled') setPrice(ltp.value);
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [symbol, tf]);

  // Draw candlestick chart on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || bars.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;
    const volumeH = 80;
    const chartH = H - volumeH - 10;

    ctx.clearRect(0, 0, W, H);

    const visible = bars.slice(-100);
    const prices = visible.flatMap(b => [b.high, b.low]);
    const minP = Math.min(...prices) * 0.998;
    const maxP = Math.max(...prices) * 1.002;
    const volumes = visible.map(b => b.volume);
    const maxVol = Math.max(...volumes);

    const barW = Math.max(4, Math.floor(W / visible.length) - 1);
    const spacing = Math.floor(W / visible.length);

    const toY = (p: number) => chartH - ((p - minP) / (maxP - minP)) * chartH;

    // Grid lines
    ctx.strokeStyle = '#2A2B35';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = (chartH / 5) * i;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      const price = maxP - ((maxP - minP) / 5) * i;
      ctx.fillStyle = '#555666';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.fillText('₹' + price.toLocaleString('en-IN', { maximumFractionDigits: 0 }), 4, y - 3);
    }

    // Candles
    visible.forEach((bar, i) => {
      const x = i * spacing + spacing / 2;
      const open = toY(bar.open);
      const close = toY(bar.close);
      const high = toY(bar.high);
      const low = toY(bar.low);
      const isGreen = bar.close >= bar.open;
      const color = isGreen ? '#00C896' : '#FF4757';

      // Wick
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, high); ctx.lineTo(x, low); ctx.stroke();

      // Body
      ctx.fillStyle = color + (isGreen ? '88' : 'AA');
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      const y0 = Math.min(open, close);
      const bodyH = Math.max(2, Math.abs(close - open));
      ctx.fillRect(x - barW / 2, y0, barW, bodyH);
      ctx.strokeRect(x - barW / 2, y0, barW, bodyH);

      // Volume
      const volH = (bar.volume / maxVol) * volumeH;
      const volY = H - volH;
      ctx.fillStyle = color + '44';
      ctx.fillRect(x - barW / 2, volY, barW, volH);
    });

    // EMA overlay (simple calculation)
    if (indicators.ema && visible.length >= 20) {
      const drawEMA = (period: number, color: string) => {
        const emas: number[] = [];
        let sum = visible.slice(0, period).reduce((a, b) => a + b.close, 0);
        emas.push(sum / period);
        const k = 2 / (period + 1);
        for (let i = period; i < visible.length; i++) {
          emas.push(visible[i].close * k + emas[emas.length - 1] * (1 - k));
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);
        ctx.beginPath();
        emas.forEach((v, i) => {
          const x = (i + period) * spacing + spacing / 2;
          const y = toY(v);
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
      };
      drawEMA(9, '#FFB800');
      drawEMA(21, '#7C5CFC');
    }
  }, [bars, indicators]);

  const ltp = price?.ltp || (bars[bars.length - 1]?.close);
  const prevClose = bars[bars.length - 2]?.close;
  const changePct = ltp && prevClose ? ((ltp - prevClose) / prevClose * 100) : 0;

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content" style={{ padding: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '16px', height: '100vh' }}>

          {/* Symbol Sidebar */}
          <div className="card" style={{ padding: 0, height: 'fit-content' }}>
            <div style={{ padding: '12px', borderBottom: '1px solid var(--border)' }}>
              <input
                className="input-field"
                style={{ width: '100%', fontSize: '13px' }}
                placeholder="Search symbol..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && search.trim()) { setSymbol(search.trim().toUpperCase()); setSearch(''); }}}
              />
            </div>
            <div style={{ padding: '6px', maxHeight: '70vh', overflow: 'auto' }}>
              {DEFAULT_SYMBOLS.filter(s => search ? s.includes(search.toUpperCase()) : true).map(s => (
                <div
                  key={s}
                  onClick={() => setSymbol(s)}
                  style={{
                    padding: '10px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '14px',
                    fontWeight: s === symbol ? '700' : '500',
                    color: s === symbol ? 'var(--accent)' : 'var(--text-primary)',
                    background: s === symbol ? 'rgba(124,92,252,0.08)' : 'transparent',
                    transition: 'all 150ms',
                  }}
                >{s}</div>
              ))}
            </div>
          </div>

          {/* Chart Area */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Price Header */}
            <div className="card" style={{ padding: '14px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '20px', fontWeight: '800', marginBottom: '2px' }}>{symbol}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>NSE • Equity</div>
                </div>
                {ltp && (
                  <>
                    <div className="price-ltp">₹{ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    <div className={changePct >= 0 ? 'price-change-pos' : 'price-change-neg'} style={{ fontSize: '18px' }}>
                      {changePct >= 0 ? '▲' : '▼'} {Math.abs(changePct).toFixed(2)}%
                    </div>
                  </>
                )}
                {/* Timeframe Tabs */}
                <div className="tab-bar" style={{ marginLeft: 'auto' }}>
                  {TIMEFRAMES.map(t => (
                    <div key={t} className={`tab-item${tf === t ? ' active' : ''}`} onClick={() => setTf(t)}>
                      {t}
                    </div>
                  ))}
                </div>
              </div>
              {/* OHLCV Row */}
              {bars.length > 0 && (() => {
                const last = bars[bars.length - 1];
                return (
                  <div style={{ display: 'flex', gap: '24px', marginTop: '10px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {[['O', last.open], ['H', last.high], ['L', last.low], ['C', last.close]].map(([k, v]) => (
                      <span key={k}><b style={{ color: 'var(--text-muted)' }}>{k}</b> <span className="mono">₹{Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></span>
                    ))}
                    <span><b style={{ color: 'var(--text-muted)' }}>Vol</b> <span className="mono">{(last.volume/1e5).toFixed(1)}L</span></span>
                  </div>
                );
              })()}
            </div>

            {/* Canvas Chart */}
            <div className="card" style={{ padding: 0, flex: 1, minHeight: '420px', position: 'relative' }}>
              <canvas
                ref={canvasRef}
                style={{ width: '100%', height: '100%', display: 'block', borderRadius: '12px' }}
              />
              {bars.length === 0 && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ fontSize: '32px' }}>📈</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading chart data...</div>
                </div>
              )}
              {/* Legend */}
              <div style={{ position: 'absolute', top: '12px', right: '12px', display: 'flex', gap: '12px', background: 'rgba(7,11,20,0.8)', padding: '6px 10px', borderRadius: '6px' }}>
                <span style={{ fontSize: '11px', color: '#FFB800' }}>── EMA9</span>
                <span style={{ fontSize: '11px', color: '#7C5CFC' }}>── EMA21</span>
              </div>
            </div>

            {/* Indicators toggle */}
            <div className="card" style={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: '600' }}>Indicators:</span>
                {Object.entries(indicators).map(([k, v]) => (
                  <button key={k} className={`badge ${v ? 'badge-accent' : 'badge-amber'}`} style={{ cursor: 'pointer', textTransform: 'capitalize' }}
                    onClick={() => setIndicators(prev => ({ ...prev, [k]: !prev[k as keyof typeof prev] }))}>
                    {v ? '✓' : '○'} {k.toUpperCase()}
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

export default function ChartPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>Loading chart...</div>}>
      <ChartContent />
    </Suspense>
  );
}
