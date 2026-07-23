import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, AlertTriangle, Wallet, TrendingUp,
  FileText, MessageSquare, Users2, ScrollText, LogOut, Building2, Cpu, Sparkles, AlertOctagon,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { caspApi } from '../../api';

const NAV = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/admin/setup', label: 'Setup Wizard', icon: Sparkles },
  { to: '/admin/compliance', label: 'KYC / KYB', icon: ShieldCheck },
  { to: '/admin/aml', label: 'AML & Alerts', icon: AlertTriangle },
  { to: '/admin/treasury', label: 'Treasury', icon: Wallet },
  { to: '/admin/otc', label: 'OTC Desk B2B', icon: TrendingUp },
  { to: '/admin/reporting', label: 'Reporting', icon: FileText },
  { to: '/admin/protection', label: 'Customer Protection', icon: MessageSquare },
  { to: '/admin/governance', label: 'Governance', icon: Users2 },
  { to: '/admin/autonomy', label: 'Autonomy', icon: Cpu },
  { to: '/admin/audit', label: 'Audit Log', icon: ScrollText },
];

export default function AdminLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [pitchMode, setPitchMode] = useState(false);

  useEffect(() => {
    (async () => {
      try { const s = await caspApi.setupStatus(); setPitchMode(!!s.pitch_mode); } catch {}
    })();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#0a0f1c] text-slate-100">
      {/* Sidebar */}
      <aside
        className="fixed inset-y-0 left-0 w-64 border-r border-slate-800 bg-[#0d1424]/80 backdrop-blur-xl flex flex-col z-30"
        data-testid="admin-sidebar"
      >
        <div className="px-6 py-5 border-b border-slate-800 flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-amber-400 to-rose-500 flex items-center justify-center">
            <Building2 className="h-5 w-5 text-slate-900" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">NeoNoble</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-amber-400/80">CASP Console</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              data-testid={`nav-${label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-amber-400/10 text-amber-300 border border-amber-400/20'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/40'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 p-4 text-xs">
          <div className="text-slate-400 mb-2 truncate" title={user?.email}>{user?.email}</div>
          <div className="flex items-center justify-between">
            <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-wider text-amber-300">
              {user?.role}
            </span>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-rose-400 inline-flex items-center gap-1"
              data-testid="admin-logout-btn"
            >
              <LogOut className="h-3.5 w-3.5" /> Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="pl-64">
        {pitchMode && (
          <div className="sticky top-0 z-30 bg-rose-600/90 backdrop-blur-sm text-white text-xs px-6 py-2 flex items-center justify-center gap-2 border-b border-rose-400"
               data-testid="pitch-mode-banner">
            <AlertOctagon className="h-4 w-4" />
            <span className="font-semibold tracking-wide">PITCH MODE — DEMO DATA, NOT VALID FOR REGULATORY USE</span>
            <span className="opacity-75">· Set CASP_PITCH_MODE=false in backend/.env to disable</span>
          </div>
        )}
        <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0a0f1c]/80 backdrop-blur-md">
          <div className="px-8 py-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">MiCAR · Reg. (EU) 2023/1114</div>
              <div className="text-sm text-slate-300">CASP Operating Stack — Shadow Mode</div>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="rounded bg-emerald-500/10 text-emerald-300 px-2 py-1 border border-emerald-500/30">
                ● Live
              </span>
              <span className="text-slate-500">v0.1.0</span>
            </div>
          </div>
        </header>
        <main className="p-8" data-testid="admin-main-content">{children}</main>
      </div>
    </div>
  );
}
