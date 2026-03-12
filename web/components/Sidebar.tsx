'use client';
import { usePathname, useRouter } from 'next/navigation';

const NAV_ITEMS = [
  { icon: '🏠', label: 'Dashboard', href: '/dashboard' },
  { icon: '🔍', label: 'Screener', href: '/screener' },
  { icon: '📈', label: 'Charts', href: '/chart' },
  { icon: '⭐', label: 'Watchlist', href: '/watchlist' },
  { icon: '🔔', label: 'Alerts', href: '/alerts' },
  { icon: '📊', label: 'Fundamentals', href: '/fundamentals' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 32, height: 32, borderRadius: '8px',
            background: 'linear-gradient(135deg, #7C5CFC, #5A3ED9)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '16px', fontWeight: '800', color: '#000',
          }}>B</div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
              BreakoutScan
            </div>
            <div style={{ fontSize: '10px', color: 'var(--accent)', fontWeight: '600', letterSpacing: '0.1em' }}>
              LIVE NSE + BSE
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <div
              key={item.href}
              className={`nav-item${isActive ? ' active' : ''}`}
              onClick={() => router.push(item.href)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </div>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
        {/* Market Status */}
        <div style={{
          padding: '10px 12px', borderRadius: '8px',
          background: 'var(--bg-primary)', border: '1px solid var(--border)',
          marginBottom: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="live-dot" />
            <span style={{ fontSize: '12px', color: 'var(--green)', fontWeight: '600' }}>Market Open</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            NSE • Closes 15:30 IST
          </div>
        </div>

        {/* User profile placeholder */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: '700', color: '#000', flexShrink: 0,
          }}>A</div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600' }}>Adarsha</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Pro Plan</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
