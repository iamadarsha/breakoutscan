'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';

interface Alert {
  id: string;
  symbol: string;
  scan_name: string;
  notify_push: boolean;
  notify_telegram?: boolean;
  is_active: boolean;
  frequency: string;
  created_at: string;
}

interface AlertHistory {
  id: string;
  symbol: string;
  scan_name: string;
  trigger_price: number;
  triggered_at: string;
  conditions_met: string[];
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [tab, setTab] = useState<'active' | 'history'>('active');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const [a, h] = await Promise.allSettled([api.getAlerts(), api.getAlertHistory()]);
      if (a.status === 'fulfilled') setAlerts(a.value);
      if (h.status === 'fulfilled') setHistory(h.value);
      setLoading(false);
    };
    load();
  }, []);

  const fmtTime = (iso: string) =>
    new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '4px' }}>Alerts</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Real-time Push + Telegram + Email alerts when scan conditions are met
            </p>
          </div>
          <button className="btn btn-primary" style={{ fontSize: '13px', padding: '8px 16px' }}>
            🔔 Create Alert
          </button>
        </div>

        {/* Summary Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
          {[
            { label: 'Active Alerts', value: alerts.filter(a => a.is_active).length, icon: '🔔', color: 'var(--accent)' },
            { label: 'Triggered Today', value: history.length, icon: '⚡', color: 'var(--green)' },
            { label: 'Paused', value: alerts.filter(a => !a.is_active).length, icon: '⏸', color: 'var(--text-secondary)' },
          ].map(stat => (
            <div key={stat.label} className="card" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ fontSize: '28px' }}>{stat.icon}</div>
              <div>
                <div style={{ fontSize: '26px', fontWeight: '800', fontFamily: 'var(--font-mono)', color: stat.color }}>{stat.value}</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{stat.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="tab-bar" style={{ marginBottom: '16px', width: 'fit-content' }}>
          <div className={`tab-item${tab === 'active' ? ' active' : ''}`} onClick={() => setTab('active')}>
            Active Alerts ({alerts.length})
          </div>
          <div className={`tab-item${tab === 'history' ? ' active' : ''}`} onClick={() => setTab('history')}>
            Trigger History ({history.length})
          </div>
        </div>

        {/* Active Alerts */}
        {tab === 'active' && (
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Scan / Condition</th>
                  <th>Notify Via</th>
                  <th>Frequency</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>{Array.from({ length: 7 }).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 14, width: '80%' }} /></td>)}</tr>
                  ))
                ) : alerts.length === 0 ? (
                  <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                    No alerts configured. Create your first alert!
                  </td></tr>
                ) : alerts.map(alert => (
                  <tr key={alert.id}>
                    <td><span style={{ fontWeight: '700', color: 'var(--accent)' }}>{alert.symbol}</span></td>
                    <td><span style={{ fontSize: '13px' }}>{alert.scan_name}</span></td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {alert.notify_push && <span className="badge badge-accent">📱 Push</span>}
                        {alert.notify_telegram && <span className="badge badge-green">✈️ Telegram</span>}
                      </div>
                    </td>
                    <td><span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{alert.frequency?.replace(/_/g, ' ')}</span></td>
                    <td>
                      <span className={`badge ${alert.is_active ? 'badge-green' : 'badge-amber'}`}>
                        {alert.is_active ? '● Active' : '⏸ Paused'}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{fmtTime(alert.created_at)}</td>
                    <td>
                      <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '4px 10px' }}>Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Trigger History */}
        {tab === 'history' && (
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Scan</th>
                  <th style={{ textAlign: 'right' }}>Trigger Price</th>
                  <th>Conditions Met</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.map(hit => (
                  <tr key={hit.id} className="scan-hit">
                    <td><span style={{ fontWeight: '700', color: 'var(--accent)' }}>{hit.symbol}</span></td>
                    <td><span style={{ fontSize: '13px' }}>{hit.scan_name}</span></td>
                    <td className="mono" style={{ textAlign: 'right', fontWeight: '600' }}>
                      ₹{hit.trigger_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {hit.conditions_met?.map((c, i) => (
                          <span key={i} className="badge badge-green" style={{ fontSize: '10px' }}>✓ {c}</span>
                        ))}
                      </div>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{fmtTime(hit.triggered_at)}</td>
                    <td>
                      <button className="btn btn-ghost" style={{ fontSize: '12px', padding: '4px 10px' }}
                        onClick={() => window.location.href=`/chart?symbol=${hit.symbol}`}>
                        View Chart →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
