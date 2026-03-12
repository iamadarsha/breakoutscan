'use client';
import { useEffect, useState } from 'react';
import api, { IndexData } from '@/lib/api';

export default function IndexBar() {
  const [indices, setIndices] = useState<IndexData[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getIndices();
        setIndices(data.slice(0, 8));
      } catch (e) {
        // Mock fallback
        setIndices([
          { name: 'NIFTY 50', ltp: 22541.30, change: 134.50, change_pct: 0.60 },
          { name: 'BANKNIFTY', ltp: 48234.75, change: -89.25, change_pct: -0.18 },
          { name: 'SENSEX', ltp: 74121.90, change: 389.40, change_pct: 0.53 },
          { name: 'NIFTY IT', ltp: 38450.00, change: 210.00, change_pct: 0.55 },
          { name: 'NIFTY AUTO', ltp: 22167.80, change: 89.60, change_pct: 0.41 },
          { name: 'NIFTY PHARMA', ltp: 19823.45, change: -127.30, change_pct: -0.64 },
          { name: 'INDIA VIX', ltp: 14.23, change: -0.89, change_pct: -5.89 },
        ]);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  const fmt = (n: number) =>
    n >= 1000 ? n.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : n.toFixed(2);

  return (
    <div className="index-bar">
      {indices.map((idx) => (
        <div className="index-card" key={idx.name}>
          <div className="index-name">{idx.name}</div>
          <div className="index-price">{fmt(idx.ltp)}</div>
          <div className={idx.change_pct >= 0 ? 'index-change-pos' : 'index-change-neg'}>
            {idx.change_pct >= 0 ? '▲' : '▼'} {Math.abs(idx.change_pct).toFixed(2)}%
          </div>
        </div>
      ))}
    </div>
  );
}
