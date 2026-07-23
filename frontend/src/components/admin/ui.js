import React from 'react';

// Lightweight, dense table optimised for back-office data display.
export function DataTable({ columns, rows, emptyText = 'No records.', testId }) {
  return (
    <div className="rounded-lg border border-slate-800 overflow-hidden bg-slate-900/30" data-testid={testId}>
      <table className="w-full text-sm">
        <thead className="bg-slate-800/40 text-slate-400 text-xs uppercase tracking-wider">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`px-4 py-2 text-left ${c.className || ''}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500">{emptyText}</td></tr>
          )}
          {rows.map((row, i) => (
            <tr key={row.id || i} className="hover:bg-slate-800/30">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 align-top ${c.cellClassName || ''}`}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Severity / status pill
export function Pill({ tone = 'slate', children }) {
  const palette = {
    slate: 'bg-slate-800 text-slate-300 border-slate-700',
    green: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    yellow: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    red: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    blue: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    purple: 'bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/30',
  }[tone] || 'bg-slate-800 text-slate-300';
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-[10px] uppercase tracking-wider border ${palette}`}>
      {children}
    </span>
  );
}

export function severityTone(sev) {
  return ({ CRITICAL: 'red', HIGH: 'red', MEDIUM: 'yellow', LOW: 'blue' }[sev] || 'slate');
}

export function statusTone(s) {
  if (!s) return 'slate';
  if (s.includes('APPROVE') || s === 'COMPLIANT' || s === 'MATCH' || s === 'ACCEPTED' || s === 'RESOLVED' || s === 'SETTLED' || s === 'EXECUTED') return 'green';
  if (s === 'PENDING' || s === 'IN_REVIEW' || s === 'QUOTED' || s === 'AWAITING_APPROVAL' || s === 'OPEN' || s === 'UNDER_REVIEW') return 'yellow';
  if (s === 'REJECTED' || s === 'CRITICAL' || s === 'BREACH' || s === 'FROZEN' || s === 'CANCELLED') return 'red';
  if (s === 'DRAFT' || s === 'GENERATED' || s === 'CLOSED' || s === 'WARNING' || s === 'CLOSED_FALSE_POSITIVE') return 'blue';
  if (s === 'SAR_FILED' || s === 'ESCALATED') return 'purple';
  return 'slate';
}

export function Card({ title, value, hint, tone, testId }) {
  return (
    <div
      className="rounded-lg border border-slate-800 bg-slate-900/40 p-5"
      data-testid={testId}
    >
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{title}</div>
      <div className={`mt-2 text-2xl font-semibold ${tone === 'amber' ? 'text-amber-300' : tone === 'red' ? 'text-rose-300' : tone === 'green' ? 'text-emerald-300' : 'text-slate-100'}`}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function SectionHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">{actions}</div>
    </div>
  );
}

export function formatEur(amount) {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat('en-EU', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(amount);
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('it-IT'); } catch { return iso; }
}
