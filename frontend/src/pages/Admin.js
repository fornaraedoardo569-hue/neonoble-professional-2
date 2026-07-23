import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AssistantWidget } from '../components/assistant/AssistantWidget';
import AdminLayout from '../components/admin/AdminLayout';
import SetupWizard from '../components/admin/SetupWizard';
import AdminWalkthrough from '../components/admin/AdminWalkthrough';
import { caspApi } from '../api';
import { Card, SectionHeader, DataTable, Pill, severityTone, statusTone, formatEur, formatDateTime } from '../components/admin/ui';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';

// ────────────────────────────────────────────────────────────────────────
// Dashboard
// ────────────────────────────────────────────────────────────────────────
function DashboardPage() {
  const [kpi, setKpi] = useState(null);
  const [audit, setAudit] = useState(null);
  const [setup, setSetup] = useState(null);
  const [forceTour, setForceTour] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [d, a, s] = await Promise.all([
          caspApi.dashboard(), caspApi.verifyAudit(), caspApi.setupStatus(),
        ]);
        setKpi(d); setAudit(a); setSetup(s);
      } catch (e) { toast.error('Failed to load dashboard'); }
    })();
  }, []);

  if (!kpi) return <div className="text-slate-400">Loading…</div>;

  return (
    <div data-testid="admin-dashboard">
      <AdminWalkthrough force={forceTour} onClose={() => setForceTour(false)} />
      <SectionHeader
        title="CASP Operations Dashboard"
        subtitle="Real-time KPIs across all 7 MiCAR operational blocks."
        actions={
          <div className="flex items-center gap-2">
            <button
              data-testid="replay-tour-btn"
              onClick={() => setForceTour(true)}
              className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 hover:border-amber-400/40 hover:text-amber-300"
            >
              ▶ Replay tour
            </button>
            <Pill tone="green">AUTONOMOUS · No third-party dependency</Pill>
          </div>
        }
      />

      {setup && setup.completeness_pct < 100 && (
        <div className="mb-6 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 flex items-center justify-between">
          <div>
            <div className="text-sm text-amber-200 font-semibold">Setup not yet complete</div>
            <div className="text-xs text-amber-100/80">
              {setup.completeness_pct}% done · {5 - setup.steps.filter(s => s.done).length} steps remaining
            </div>
          </div>
          <a href="/admin/setup" className="px-3 py-1.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/40 text-sm hover:bg-amber-500/30">
            Open Setup Wizard →
          </a>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <Card testId="kpi-kyc-pending" title="KYC Pending" value={kpi.kyc.pending} hint={`${kpi.kyc.approved} approved`} tone="amber" />
        <Card testId="kpi-aml-open" title="AML Open Alerts" value={kpi.aml.open_alerts} hint={`${kpi.aml.critical} critical`} tone="red" />
        <Card testId="kpi-otc-pending" title="OTC Pending" value={kpi.otc.pending} hint={`${formatEur(kpi.otc.volume_30d_eur)} settled 30d`} tone="amber" />
        <Card testId="kpi-wallets" title="Custodial Wallets" value={kpi.wallets.total} hint="hot + cold" />
        <Card testId="kpi-complaints" title="Open Complaints" value={kpi.complaints.open} hint="SLA 15d" />
        <Card
          testId="kpi-capital"
          title="Capital Adequacy"
          value={kpi.capital ? formatEur(kpi.capital.own_funds_eur) : '—'}
          hint={kpi.capital ? `${kpi.capital.status} · ${(kpi.capital.coverage_ratio * 100).toFixed(0)}% of €${kpi.capital.required_capital_eur.toLocaleString()}` : ''}
          tone={kpi.capital?.status === 'COMPLIANT' ? 'green' : 'red'}
        />
        <Card
          testId="kpi-audit"
          title="Audit Chain"
          value={audit?.verified ? 'VERIFIED' : 'BROKEN'}
          hint={audit ? `${audit.checked} entries` : ''}
          tone={audit?.verified ? 'green' : 'red'}
        />
      </div>

      <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-3">MiCAR Operational Blocks</h2>
          <ul className="space-y-2 text-sm text-slate-400">
            {[
              ['BLOCK 1', 'Identity & Onboarding', 'Sumsub (KYC) + Onfido alt. ready'],
              ['BLOCK 2', 'Transaction Monitoring & AML', 'Chainalysis KYT + Notabene TR'],
              ['BLOCK 3', 'Custody & Treasury', 'Fireblocks MPC + PoR Merkle'],
              ['BLOCK 4', 'Order Management (B2B OTC)', '4-eye approval > €50k'],
              ['BLOCK 5', 'Regulatory Reporting & Audit', 'MiCAR T+1 + WORM hash-chain'],
              ['BLOCK 6', 'Customer Protection', '15-day SLA + disclosures'],
              ['BLOCK 7', 'Internal Governance (RBAC)', 'MLRO / Risk / Treasury roles'],
            ].map(([n, t, d]) => (
              <li key={n} className="border border-slate-800 rounded px-3 py-2 flex items-center justify-between">
                <div>
                  <div className="text-xs text-amber-400 font-mono">{n}</div>
                  <div className="text-slate-200">{t}</div>
                </div>
                <div className="text-xs text-slate-500">{d}</div>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-3">Notes</h2>
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-100/80">
            <div className="font-semibold mb-2">Shadow CASP mode</div>
            This console operates in shadow mode: all 7 blocks are fully wired against
            mock providers (Sumsub / Chainalysis / Fireblocks / Notabene). Set
            <code className="mx-1 px-1 rounded bg-slate-800">SUMSUB_LIVE=true</code>
            (and equivalent env vars) once partner contracts are active to switch any
            adapter to LIVE without code changes.
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Compliance — KYC / KYB / Risk Rating
// ────────────────────────────────────────────────────────────────────────
function CompliancePage() {
  const [tab, setTab] = useState('kyc');
  const [kyc, setKyc] = useState([]);
  const [kyb, setKyb] = useState([]);
  const [risk, setRisk] = useState([]);
  const [sanctions, setSanctions] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    try {
      const [k, b, r, s] = await Promise.all([
        caspApi.listKyc(), caspApi.listKyb(), caspApi.listRisk(), caspApi.listSanctions(),
      ]);
      setKyc(k); setKyb(b); setRisk(r); setSanctions(s);
    } catch (e) { toast.error('Load failed'); }
    finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, []);

  const decideKyc = async (id, decision) => {
    try {
      await caspApi.decideKyc(id, decision, decision === 'REJECT' ? 'Manual rejection from admin console' : null);
      toast.success(`KYC ${decision}D`);
      reload();
    } catch (e) { toast.error('Action failed'); }
  };

  return (
    <div data-testid="admin-compliance">
      <SectionHeader title="Compliance — KYC / KYB / Risk / Sanctions" subtitle="MiCAR Art. 68 + AMLD6 Art. 18/30." />
      <div className="flex gap-2 mb-4 text-sm">
        {['kyc', 'kyb', 'risk', 'sanctions'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            data-testid={`compliance-tab-${t}`}
            className={`px-3 py-1.5 rounded border ${tab === t ? 'border-amber-400/40 bg-amber-400/10 text-amber-300' : 'border-slate-800 text-slate-400 hover:text-slate-200'}`}
          >
            {t.toUpperCase()} <span className="ml-1 text-xs text-slate-500">({{ kyc, kyb, risk, sanctions }[t].length})</span>
          </button>
        ))}
      </div>

      {loading ? <div className="text-slate-500">Loading…</div> :
        tab === 'kyc' ? (
          <DataTable testId="kyc-table" rows={kyc} columns={[
            { key: 'full_name', label: 'Customer' },
            { key: 'tier', label: 'Tier', render: (r) => <Pill tone="blue">{r.tier}</Pill> },
            { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
            { key: 'country_of_residence', label: 'Country' },
            { key: 'submitted_at', label: 'Submitted', render: (r) => <span className="text-slate-400">{formatDateTime(r.submitted_at)}</span> },
            {
              key: 'actions', label: 'Action', render: (r) => r.status === 'PENDING' || r.status === 'IN_REVIEW' ? (
                <div className="flex gap-2">
                  <button data-testid={`kyc-approve-${r.id}`} onClick={() => decideKyc(r.id, 'APPROVE')} className="text-xs px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20">Approve</button>
                  <button data-testid={`kyc-reject-${r.id}`} onClick={() => decideKyc(r.id, 'REJECT')} className="text-xs px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20">Reject</button>
                </div>
              ) : <span className="text-slate-600 text-xs">—</span>
            },
          ]} />
        ) :
        tab === 'kyb' ? (
          <DataTable testId="kyb-table" rows={kyb} columns={[
            { key: 'legal_name', label: 'Legal Name' },
            { key: 'country_of_incorporation', label: 'Country' },
            { key: 'lei', label: 'LEI' },
            { key: 'expected_monthly_volume_eur', label: 'Expected Vol/mo', render: (r) => formatEur(r.expected_monthly_volume_eur) },
            { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
          ]} />
        ) :
        tab === 'risk' ? (
          <DataTable testId="risk-table" rows={risk} columns={[
            { key: 'user_id', label: 'User', render: (r) => <code className="text-xs text-slate-400">{r.user_id.slice(0, 8)}…</code> },
            { key: 'rating', label: 'Rating', render: (r) => <Pill tone={r.rating === 'LOW' ? 'green' : r.rating === 'HIGH' ? 'red' : r.rating === 'PROHIBITED' ? 'red' : 'yellow'}>{r.rating}</Pill> },
            { key: 'score', label: 'Score', render: (r) => <span className="font-mono">{r.score}</span> },
            { key: 'next_review_at', label: 'Next Review', render: (r) => formatDateTime(r.next_review_at) },
          ]} />
        ) : (
          <DataTable testId="sanctions-table" rows={sanctions} columns={[
            { key: 'list_name', label: 'List' },
            { key: 'match_type', label: 'Type' },
            { key: 'matched_name', label: 'Matched Name' },
            { key: 'match_score', label: 'Score', render: (r) => <span className="font-mono">{r.match_score}</span> },
            { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
          ]} />
        )
      }
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// AML & Alerts
// ────────────────────────────────────────────────────────────────────────
function AmlPage() {
  const [alerts, setAlerts] = useState([]);
  const [travel, setTravel] = useState([]);
  const [sars, setSars] = useState([]);
  const [tab, setTab] = useState('alerts');
  const [screenAddr, setScreenAddr] = useState('');

  const reload = async () => {
    try {
      const [a, t, s] = await Promise.all([
        caspApi.listAml(), caspApi.listTravelRule(), caspApi.listSar(),
      ]);
      setAlerts(a); setTravel(t); setSars(s);
    } catch { toast.error('Load failed'); }
  };
  useEffect(() => { reload(); }, []);

  const screen = async () => {
    if (!screenAddr) return;
    try {
      const r = await caspApi.screenAddress({ address: screenAddr, asset: 'USDC', chain: 'BSC' });
      toast[ r.is_critical ? 'error' : 'success' ](
        r.is_critical ? `🚨 CRITICAL — ${r.risk_score}/100` : `Clear — score ${r.risk_score}/100`
      );
      setScreenAddr('');
      reload();
    } catch { toast.error('Screen failed'); }
  };

  const resolve = async (id, status) => {
    try { await caspApi.resolveAml(id, status, 'Resolved from console'); toast.success('Resolved'); reload(); }
    catch { toast.error('Action failed'); }
  };

  return (
    <div data-testid="admin-aml">
      <SectionHeader
        title="AML & Transaction Monitoring"
        subtitle="Chainalysis KYT + Notabene Travel Rule + SAR drafts."
        actions={
          <div className="flex gap-2 items-center">
            <input
              data-testid="aml-screen-input"
              value={screenAddr}
              onChange={(e) => setScreenAddr(e.target.value)}
              placeholder="0x… wallet to screen"
              className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm w-72 font-mono"
            />
            <button data-testid="aml-screen-btn" onClick={screen} className="px-3 py-1.5 bg-amber-400/10 text-amber-300 border border-amber-400/30 rounded text-sm hover:bg-amber-400/20">
              Screen
            </button>
          </div>
        }
      />

      <div className="flex gap-2 mb-4 text-sm">
        {[['alerts', alerts.length], ['travel', travel.length], ['sar', sars.length]].map(([t, n]) => (
          <button key={t} onClick={() => setTab(t)} data-testid={`aml-tab-${t}`}
            className={`px-3 py-1.5 rounded border ${tab === t ? 'border-amber-400/40 bg-amber-400/10 text-amber-300' : 'border-slate-800 text-slate-400 hover:text-slate-200'}`}>
            {t.toUpperCase()} <span className="ml-1 text-xs text-slate-500">({n})</span>
          </button>
        ))}
      </div>

      {tab === 'alerts' && (
        <DataTable testId="alerts-table" rows={alerts} columns={[
          { key: 'rule_name', label: 'Rule' },
          { key: 'severity', label: 'Severity', render: (r) => <Pill tone={severityTone(r.severity)}>{r.severity}</Pill> },
          { key: 'amount_eur', label: 'Amount', render: (r) => formatEur(r.amount_eur) },
          { key: 'risk_score', label: 'Risk', render: (r) => <span className="font-mono">{r.risk_score?.toFixed?.(0)}</span> },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
          {
            key: 'a', label: 'Action', render: (r) => r.status === 'OPEN' ? (
              <div className="flex gap-2">
                <button data-testid={`aml-close-fp-${r.id}`} onClick={() => resolve(r.id, 'CLOSED_FALSE_POSITIVE')} className="text-xs px-2 py-1 rounded bg-slate-700/40 text-slate-300 border border-slate-700">False+</button>
                <button data-testid={`aml-escalate-${r.id}`} onClick={() => resolve(r.id, 'ESCALATED')} className="text-xs px-2 py-1 rounded bg-fuchsia-500/10 text-fuchsia-300 border border-fuchsia-500/30">Escalate</button>
              </div>
            ) : '—'
          },
        ]} />
      )}

      {tab === 'travel' && (
        <DataTable testId="travel-table" rows={travel} emptyText="No Travel Rule transfers yet." columns={[
          { key: 'direction', label: 'Dir' },
          { key: 'asset', label: 'Asset' },
          { key: 'amount_eur', label: 'EUR', render: (r) => formatEur(r.amount_eur) },
          { key: 'counterparty_vasp', label: 'Counterparty VASP' },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
          { key: 'created_at', label: 'When', render: (r) => formatDateTime(r.created_at) },
        ]} />
      )}

      {tab === 'sar' && (
        <DataTable testId="sar-table" rows={sars} emptyText="No SAR drafts yet." columns={[
          { key: 'sar_number', label: 'SAR #' },
          { key: 'narrative', label: 'Narrative', render: (r) => <span className="line-clamp-2 text-slate-300">{r.narrative}</span> },
          { key: 'total_amount_eur', label: 'Total', render: (r) => formatEur(r.total_amount_eur) },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        ]} />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Treasury — wallets, reconciliation, PoR
// ────────────────────────────────────────────────────────────────────────
function TreasuryPage() {
  const [wallets, setWallets] = useState([]);
  const [por, setPor] = useState(null);

  const reload = async () => {
    try {
      const [w, p] = await Promise.all([caspApi.listWallets(), caspApi.latestPor()]);
      setWallets(w); setPor(p);
    } catch { toast.error('Load failed'); }
  };
  useEffect(() => { reload(); }, []);

  const generate = async () => { try { await caspApi.generatePor(); toast.success('PoR generated'); reload(); } catch { toast.error('PoR failed'); } };
  const reconcile = async (id) => { try { const r = await caspApi.reconcileWallet(id); toast[r.status === 'MATCH' ? 'success' : 'warning'](`Reconciliation: ${r.status}`); reload(); } catch { toast.error('Reconcile failed'); } };
  const freeze = async (id) => { try { await caspApi.freezeWallet(id); toast.success('Wallet frozen'); reload(); } catch { toast.error('Freeze failed'); } };

  return (
    <div data-testid="admin-treasury">
      <SectionHeader
        title="Treasury — Custody & Reserves"
        subtitle="Fireblocks MPC vaults · Proof-of-Reserves (Merkle) · Daily reconciliation."
        actions={
          <button data-testid="por-generate-btn" onClick={generate} className="px-3 py-1.5 bg-amber-400/10 text-amber-300 border border-amber-400/30 rounded text-sm hover:bg-amber-400/20">
            Generate PoR Snapshot
          </button>
        }
      />

      {por && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card testId="por-coverage" title="PoR Coverage" value={`${(por.coverage_ratio * 100).toFixed(0)}%`} tone={por.coverage_ratio >= 1 ? 'green' : 'red'} hint={`as of ${formatDateTime(por.snapshot_date)}`} />
          <Card testId="por-assets" title="Total Assets" value={formatEur(por.total_assets_eur)} />
          <Card testId="por-liab" title="Total Liabilities" value={formatEur(por.total_liabilities_eur)} />
          <Card testId="por-merkle" title="Merkle Root" value={<code className="text-xs">{por.merkle_root?.slice(0, 14)}…</code>} hint={`${por.leaves_count} leaves`} />
        </div>
      )}

      <DataTable testId="wallets-table" rows={wallets} columns={[
        { key: 'kind', label: 'Kind', render: (r) => <Pill tone={r.kind === 'COLD' ? 'blue' : 'yellow'}>{r.kind}</Pill> },
        { key: 'asset', label: 'Asset' },
        { key: 'chain', label: 'Chain' },
        { key: 'address', label: 'Address', render: (r) => <code className="text-xs text-slate-400">{r.address.slice(0, 10)}…{r.address.slice(-6)}</code> },
        { key: 'purpose', label: 'Purpose', render: (r) => <span className="text-xs text-slate-400">{r.purpose}</span> },
        { key: 'balance_eur', label: 'EUR Balance', render: (r) => formatEur(r.balance_eur) },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        {
          key: 'a', label: 'Actions', render: (r) => (
            <div className="flex gap-2">
              <button data-testid={`reconcile-${r.id}`} onClick={() => reconcile(r.id)} className="text-xs px-2 py-1 rounded bg-slate-700/40 text-slate-300 border border-slate-700">Reconcile</button>
              {r.status !== 'FROZEN' && <button data-testid={`freeze-${r.id}`} onClick={() => freeze(r.id)} className="text-xs px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30">Freeze</button>}
            </div>
          )
        },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// OTC B2B
// ────────────────────────────────────────────────────────────────────────
function OtcPage() {
  const [list, setList] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ client_user_id: '', side: 'BUY', asset: 'BTC', quantity: '', price_eur: '' });

  const reload = async () => { try { setList(await caspApi.listOtc()); } catch { toast.error('Load failed'); } };
  useEffect(() => { reload(); }, []);

  const submit = async () => {
    try {
      await caspApi.createOtc({ ...form, quantity: parseFloat(form.quantity), price_eur: parseFloat(form.price_eur) });
      toast.success('OTC quote created');
      setShowForm(false);
      setForm({ client_user_id: '', side: 'BUY', asset: 'BTC', quantity: '', price_eur: '' });
      reload();
    } catch { toast.error('Quote creation failed'); }
  };
  const approve = async (id) => { try { await caspApi.approveOtc(id, 'APPROVE', 'OK from MLRO'); toast.success('Approved'); reload(); } catch (e) { toast.error(e.response?.data?.detail?.detail || 'Approve failed'); } };
  const execute = async (id) => { try { await caspApi.executeOtc(id); toast.success('Executed'); reload(); } catch (e) { toast.error(e.response?.data?.detail?.detail || 'Execute failed'); } };

  return (
    <div data-testid="admin-otc">
      <SectionHeader
        title="OTC Desk B2B"
        subtitle="Institutional buy/sell with 4-eye approval > €50k · Best-execution evidence captured."
        actions={
          <button data-testid="otc-new-btn" onClick={() => setShowForm((v) => !v)} className="px-3 py-1.5 bg-amber-400/10 text-amber-300 border border-amber-400/30 rounded text-sm hover:bg-amber-400/20">
            {showForm ? 'Cancel' : '+ New Quote'}
          </button>
        }
      />

      {showForm && (
        <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            <input data-testid="otc-form-client" placeholder="Client user_id" value={form.client_user_id} onChange={(e) => setForm({ ...form, client_user_id: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5" />
            <select data-testid="otc-form-side" value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5">
              <option>BUY</option><option>SELL</option>
            </select>
            <select data-testid="otc-form-asset" value={form.asset} onChange={(e) => setForm({ ...form, asset: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5">
              {['BTC', 'ETH', 'NENO', 'USDC', 'USDT'].map(a => <option key={a}>{a}</option>)}
            </select>
            <input data-testid="otc-form-qty" type="number" placeholder="Quantity" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5" />
            <input data-testid="otc-form-price" type="number" placeholder="Price EUR" value={form.price_eur} onChange={(e) => setForm({ ...form, price_eur: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5" />
          </div>
          <div className="mt-3 flex justify-end">
            <button data-testid="otc-form-submit" onClick={submit} className="px-3 py-1.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded text-sm hover:bg-emerald-500/20">Create Quote</button>
          </div>
        </div>
      )}

      <DataTable testId="otc-table" rows={list} columns={[
        { key: 'reference', label: 'Ref' },
        { key: 'side', label: 'Side', render: (r) => <Pill tone={r.side === 'BUY' ? 'green' : 'yellow'}>{r.side}</Pill> },
        { key: 'asset', label: 'Asset' },
        { key: 'quantity', label: 'Qty', render: (r) => <span className="font-mono">{r.quantity}</span> },
        { key: 'price_eur', label: 'Price', render: (r) => formatEur(r.price_eur) },
        { key: 'total_eur', label: 'Total', render: (r) => formatEur(r.total_eur) },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        {
          key: 'a', label: 'Action', render: (r) => (
            <div className="flex gap-2">
              {r.status === 'AWAITING_APPROVAL' && <button data-testid={`otc-approve-${r.id}`} onClick={() => approve(r.id)} className="text-xs px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">Approve</button>}
              {(r.status === 'QUOTED' || r.status === 'APPROVED') && <button data-testid={`otc-execute-${r.id}`} onClick={() => execute(r.id)} className="text-xs px-2 py-1 rounded bg-sky-500/10 text-sky-300 border border-sky-500/30">Execute</button>}
            </div>
          )
        },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Reporting (MiCAR + Capital)
// ────────────────────────────────────────────────────────────────────────
function ReportingPage() {
  const [reports, setReports] = useState([]);
  useEffect(() => { (async () => { try { setReports(await caspApi.listReports()); } catch {} })(); }, []);
  const gen = async () => {
    const end = new Date();
    const start = new Date(); start.setDate(start.getDate() - 30);
    try {
      await caspApi.generateMicar({ period_start: start.toISOString(), period_end: end.toISOString() });
      toast.success('MiCAR report generated');
      setReports(await caspApi.listReports());
    } catch { toast.error('Generate failed'); }
  };
  return (
    <div data-testid="admin-reporting">
      <SectionHeader
        title="Regulatory Reporting & Capital Adequacy"
        subtitle="MiCAR T+1 reports · CONSOB quarterly · Capital snapshot (€50k / €125k / €150k thresholds)."
        actions={<button data-testid="micar-gen-btn" onClick={gen} className="px-3 py-1.5 bg-amber-400/10 text-amber-300 border border-amber-400/30 rounded text-sm hover:bg-amber-400/20">Generate MiCAR Report</button>}
      />
      <DataTable testId="reports-table" rows={reports} columns={[
        { key: 'report_type', label: 'Type' },
        { key: 'period_start', label: 'From', render: (r) => formatDateTime(r.period_start) },
        { key: 'period_end', label: 'To', render: (r) => formatDateTime(r.period_end) },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        {
          key: 'summary', label: 'Summary', render: (r) => (
            <div className="text-xs text-slate-400">
              {r.summary?.otc_transactions ?? 0} tx · {formatEur(r.summary?.otc_volume_eur || 0)} · {r.summary?.sar_filed ?? 0} SAR
            </div>
          )
        },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Customer Protection
// ────────────────────────────────────────────────────────────────────────
function ProtectionPage() {
  const [complaints, setComplaints] = useState([]);
  const [disclosures, setDisclosures] = useState([]);
  useEffect(() => { (async () => { try { setComplaints(await caspApi.listComplaints()); setDisclosures(await caspApi.listDisclosures()); } catch {} })(); }, []);
  return (
    <div data-testid="admin-protection">
      <SectionHeader title="Customer Protection (MiCAR Art. 66 + 71)" subtitle="15-day complaint SLA · Pre-contractual disclosures per asset." />
      <h2 className="text-sm font-semibold text-slate-200 mb-3">Complaints</h2>
      <DataTable testId="complaints-table" rows={complaints} columns={[
        { key: 'reference', label: 'Ref' },
        { key: 'category', label: 'Category' },
        { key: 'subject', label: 'Subject' },
        { key: 'sla_deadline', label: 'SLA Deadline', render: (r) => formatDateTime(r.sla_deadline) },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
      ]} />
      <h2 className="text-sm font-semibold text-slate-200 mt-8 mb-3">Asset Disclosures</h2>
      <DataTable testId="disclosures-table" rows={disclosures} columns={[
        { key: 'asset', label: 'Asset' },
        { key: 'asset_chain', label: 'Chain' },
        { key: 'risk_level', label: 'Risk', render: (r) => <Pill tone={r.risk_level === 'LOW' ? 'green' : r.risk_level === 'MEDIUM' ? 'yellow' : 'red'}>{r.risk_level}</Pill> },
        { key: 'version', label: 'Version' },
        { key: 'published_at', label: 'Published', render: (r) => formatDateTime(r.published_at) },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Governance
// ────────────────────────────────────────────────────────────────────────
function GovernancePage() {
  const [admins, setAdmins] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  useEffect(() => {
    (async () => {
      try {
        const [a, i, c] = await Promise.all([caspApi.listAdmins(), caspApi.listIncidents(), caspApi.listConflicts()]);
        setAdmins(a); setIncidents(i); setConflicts(c);
      } catch {}
    })();
  }, []);
  return (
    <div data-testid="admin-governance">
      <SectionHeader title="Internal Governance & RBAC" subtitle="Admin users · Operational incidents (DORA) · Conflicts of interest (Art. 72)." />
      <h2 className="text-sm font-semibold text-slate-200 mb-3">Admin Users (RBAC)</h2>
      <DataTable testId="admins-table" rows={admins} columns={[
        { key: 'email', label: 'Email' },
        { key: 'department', label: 'Department' },
        { key: 'casp_roles', label: 'Roles', render: (r) => <div className="flex flex-wrap gap-1">{r.casp_roles.map((x) => <Pill key={x} tone="purple">{x}</Pill>)}</div> },
        { key: 'is_active', label: 'Active', render: (r) => <Pill tone={r.is_active ? 'green' : 'slate'}>{r.is_active ? 'YES' : 'NO'}</Pill> },
      ]} />

      <h2 className="text-sm font-semibold text-slate-200 mt-8 mb-3">Operational Incidents</h2>
      <DataTable testId="incidents-table" rows={incidents} columns={[
        { key: 'reference', label: 'Ref' },
        { key: 'title', label: 'Title' },
        { key: 'severity', label: 'Sev', render: (r) => <Pill tone={r.severity === 'SEV1' ? 'red' : r.severity === 'SEV2' ? 'red' : r.severity === 'SEV3' ? 'yellow' : 'blue'}>{r.severity}</Pill> },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        { key: 'detected_at', label: 'Detected', render: (r) => formatDateTime(r.detected_at) },
      ]} />

      <h2 className="text-sm font-semibold text-slate-200 mt-8 mb-3">Conflicts of Interest</h2>
      <DataTable testId="conflicts-table" rows={conflicts} columns={[
        { key: 'party', label: 'Party' },
        { key: 'nature', label: 'Nature' },
        { key: 'mitigation', label: 'Mitigation' },
        { key: 'declared_at', label: 'Declared', render: (r) => formatDateTime(r.declared_at) },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Audit log
// ────────────────────────────────────────────────────────────────────────
function AuditPage() {
  const [log, setLog] = useState([]);
  const [verify, setVerify] = useState(null);
  useEffect(() => { (async () => { try { setLog(await caspApi.listAudit(200)); setVerify(await caspApi.verifyAudit()); } catch {} })(); }, []);
  return (
    <div data-testid="admin-audit">
      <SectionHeader
        title="Immutable Audit Log (WORM)"
        subtitle="SHA-256 hash-chained · CONSOB-grade evidence trail."
        actions={verify && <Pill tone={verify.verified ? 'green' : 'red'}>{verify.verified ? `CHAIN VERIFIED · ${verify.checked} entries` : 'CHAIN BROKEN'}</Pill>}
      />
      <DataTable testId="audit-table" rows={log} columns={[
        { key: 'sequence', label: '#', render: (r) => <span className="font-mono text-slate-400">{r.sequence}</span> },
        { key: 'created_at', label: 'When', render: (r) => formatDateTime(r.created_at) },
        { key: 'actor_email', label: 'Actor', render: (r) => <span className="text-slate-400">{r.actor_email || r.actor_id}</span> },
        { key: 'action', label: 'Action', render: (r) => <Pill tone="blue">{r.action}</Pill> },
        { key: 'entity_type', label: 'Entity' },
        { key: 'hash', label: 'Hash', render: (r) => <code className="text-xs text-slate-500">{r.hash?.slice(0, 12)}…</code> },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Autonomy — sanctions list, VASP directory, TRP inbox, KYT live tester
// ────────────────────────────────────────────────────────────────────────
function AutonomyPage() {
  const [status, setStatus] = useState(null);
  const [vasps, setVasps] = useState([]);
  const [inbox, setInbox] = useState([]);
  const [testAddr, setTestAddr] = useState('0x8589427373d6d84e98730d7795d8f6f8731fda16');
  const [testResult, setTestResult] = useState(null);
  const [showVaspForm, setShowVaspForm] = useState(false);
  const [vaspForm, setVaspForm] = useState({
    did: '', name: '', trp_endpoint: '',
    known_addresses: '', shared_secret: '',
  });

  const reload = async () => {
    try {
      const [s, v, i] = await Promise.all([
        caspApi.sanctionsStatus(), caspApi.listVasps(), caspApi.listTrpInbox(),
      ]);
      setStatus(s); setVasps(v); setInbox(i);
    } catch (e) { toast.error('Load failed'); }
  };
  useEffect(() => { reload(); }, []);

  const refresh = async () => {
    try { await caspApi.sanctionsRefresh(); toast.success('Sanctions refresh logged'); reload(); }
    catch { toast.error('Refresh failed'); }
  };
  const test = async () => {
    try {
      const r = await caspApi.screenAddress({ address: testAddr, asset: 'USDC', chain: 'BSC' });
      setTestResult(r);
    } catch { toast.error('Screen failed'); }
  };

  const submitVasp = async () => {
    if (!vaspForm.did || !vaspForm.name || !vaspForm.trp_endpoint || !vaspForm.shared_secret) {
      toast.error('DID, name, TRP endpoint and shared secret are required');
      return;
    }
    try {
      await caspApi.upsertVasp({
        ...vaspForm,
        known_addresses: vaspForm.known_addresses
          .split(/[\s,]+/).map(a => a.trim()).filter(Boolean),
      });
      toast.success(`VASP ${vaspForm.name} saved`);
      setShowVaspForm(false);
      setVaspForm({ did: '', name: '', trp_endpoint: '', known_addresses: '', shared_secret: '' });
      reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    }
  };

  const removeVasp = async (did) => {
    if (!window.confirm(`Remove VASP ${did}?`)) return;
    try { await caspApi.deleteVasp(did); toast.success('VASP removed'); reload(); }
    catch { toast.error('Delete failed'); }
  };

  const decideTrp = async (id, decision) => {
    try {
      await caspApi.decideTrpInbox(id, decision, `${decision} via admin console`);
      toast.success(`Travel Rule message ${decision}ED`);
      reload();
    } catch { toast.error('Decision failed'); }
  };

  return (
    <div data-testid="admin-autonomy">
      <SectionHeader
        title="Autonomous Operation"
        subtitle="100% in-house — no Sumsub / Chainalysis / Fireblocks / Notabene dependency. All four functions are performed by internal adapters under services/casp/internal/."
        actions={status?.autonomous ? <Pill tone="green">AUTONOMOUS MODE</Pill> : <Pill tone="red">VENDOR MODE</Pill>}
      />

      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card testId="auto-ofac" title="OFAC Crypto Addresses" value={status.ofac_crypto_addresses} hint="bundled, refreshable" tone="amber" />
          <Card testId="auto-mixers" title="Known Mixers" value={status.known_mixers} hint="Tornado Cash et al." />
          <Card testId="auto-pep" title="Sanctioned Individuals" value={status.sanctioned_individuals} hint="OFAC SDN + EU + UN" />
          <Card testId="auto-refresh" title="Last Refresh" value={status.last_refresh_at ? formatDateTime(status.last_refresh_at) : 'never'} hint={status.source} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-200">In-house KYT Tester</h2>
            <button data-testid="autonomy-refresh-btn" onClick={refresh} className="text-xs px-2 py-1 rounded bg-amber-400/10 text-amber-300 border border-amber-400/30">
              Refresh Sanctions
            </button>
          </div>
          <div className="flex gap-2 mb-3">
            <input
              data-testid="autonomy-test-input"
              value={testAddr}
              onChange={(e) => setTestAddr(e.target.value)}
              placeholder="0x… address to screen"
              className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm font-mono"
            />
            <button data-testid="autonomy-test-btn" onClick={test} className="px-3 py-1.5 bg-amber-400/10 text-amber-300 border border-amber-400/30 rounded text-sm">
              Screen
            </button>
          </div>
          {testResult && (
            <div className={`rounded p-3 border ${testResult.is_critical ? 'border-rose-500/40 bg-rose-500/5 text-rose-200' : 'border-emerald-500/40 bg-emerald-500/5 text-emerald-200'}`}>
              <div className="flex items-center gap-2 text-sm mb-1">
                {testResult.is_critical ? '🚨 CRITICAL' : '✅ CLEAR'}
                <span className="font-mono">{testResult.risk_score}/100</span>
                <span className="text-xs text-slate-400">via {testResult.provider}</span>
              </div>
              {testResult.categories?.length > 0 && (
                <div className="text-xs text-slate-300">{testResult.categories.map(c => c.name).join(', ')}</div>
              )}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-300">
          <h2 className="text-sm font-semibold text-slate-200 mb-2">Why autonomous</h2>
          <ul className="space-y-2 text-slate-400">
            <li>• No vendor lock-in — all four CASP functions run on internal code.</li>
            <li>• €0 recurring SaaS fees (vs €3–8k/mo × 4 providers in vendor mode).</li>
            <li>• Free public data sources only: OFAC SDN, EU & UN consolidated lists, BscScan / Etherscan free API, IVMS-101 open standard.</li>
            <li>• Each vendor can still be optionally enabled at any time via <code>SUMSUB_LIVE=true</code>, <code>CHAINALYSIS_LIVE=true</code>, etc. — without code change.</li>
          </ul>
        </div>
      </div>

      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200">Peer VASP Directory (Travel Rule)</h2>
        <button
          data-testid="vasp-new-btn"
          onClick={() => setShowVaspForm((v) => !v)}
          className="text-xs px-3 py-1.5 rounded bg-amber-400/10 text-amber-300 border border-amber-400/30 hover:bg-amber-400/20"
        >
          {showVaspForm ? 'Cancel' : '+ Add VASP'}
        </button>
      </div>

      {showVaspForm && (
        <div className="mb-4 rounded-lg border border-amber-400/20 bg-amber-400/5 p-4" data-testid="vasp-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <input
              data-testid="vasp-form-did" placeholder="DID — e.g. did:web:binance.com"
              value={vaspForm.did}
              onChange={(e) => setVaspForm({ ...vaspForm, did: e.target.value })}
              className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 font-mono"
            />
            <input
              data-testid="vasp-form-name" placeholder="VASP name — e.g. Binance"
              value={vaspForm.name}
              onChange={(e) => setVaspForm({ ...vaspForm, name: e.target.value })}
              className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5"
            />
            <input
              data-testid="vasp-form-endpoint" placeholder="TRP endpoint — https://… /trp/inbox"
              value={vaspForm.trp_endpoint}
              onChange={(e) => setVaspForm({ ...vaspForm, trp_endpoint: e.target.value })}
              className="md:col-span-2 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 font-mono"
            />
            <input
              data-testid="vasp-form-addresses" placeholder="Known wallet addresses (comma-separated)"
              value={vaspForm.known_addresses}
              onChange={(e) => setVaspForm({ ...vaspForm, known_addresses: e.target.value })}
              className="md:col-span-2 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 font-mono"
            />
            <input
              data-testid="vasp-form-secret"
              type="password" placeholder="Shared HMAC secret (exchange via secure channel!)"
              value={vaspForm.shared_secret}
              onChange={(e) => setVaspForm({ ...vaspForm, shared_secret: e.target.value })}
              className="md:col-span-2 bg-slate-900 border border-rose-500/30 rounded px-3 py-1.5"
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
            <span>🔐 The shared secret is never displayed back in the list. Store it securely.</span>
            <button
              data-testid="vasp-form-submit"
              onClick={submitVasp}
              className="px-3 py-1.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20"
            >
              Save VASP
            </button>
          </div>
        </div>
      )}

      <DataTable testId="autonomy-vasps" rows={vasps} columns={[
        { key: 'name', label: 'VASP' },
        { key: 'did', label: 'DID', render: (r) => <code className="text-xs text-slate-400">{r.did}</code> },
        { key: 'trp_endpoint', label: 'TRP Endpoint', render: (r) => <code className="text-xs text-slate-400">{r.trp_endpoint}</code> },
        { key: 'known_addresses', label: 'Known Addrs', render: (r) => <span className="font-mono text-xs">{r.known_addresses?.length || 0}</span> },
        { key: 'verified', label: 'Verified', render: (r) => <Pill tone={r.verified ? 'green' : 'yellow'}>{r.verified ? 'YES' : 'NO'}</Pill> },
        {
          key: 'a', label: 'Action', render: (r) => (
            <button
              data-testid={`vasp-delete-${r.did}`}
              onClick={() => removeVasp(r.did)}
              className="text-xs px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20"
            >
              Remove
            </button>
          ),
        },
      ]} />

      <h2 className="text-sm font-semibold text-slate-200 mt-8 mb-3">Inbound Travel Rule Messages</h2>
      <DataTable testId="autonomy-trp-inbox" rows={inbox} emptyText="No inbound TRP messages yet." columns={[
        { key: 'received_at', label: 'When', render: (r) => formatDateTime(r.received_at) },
        { key: 'peer_did', label: 'From VASP', render: (r) => <code className="text-xs text-slate-400">{r.peer_did}</code> },
        { key: 'verified', label: 'Signature', render: (r) => <Pill tone={r.verified ? 'green' : 'red'}>{r.verified ? 'VERIFIED' : 'INVALID'}</Pill> },
        { key: 'status', label: 'Status', render: (r) => <Pill tone={statusTone(r.status)}>{r.status}</Pill> },
        { key: 'asset', label: 'Asset', render: (r) => r.payload?.transfer?.asset || '—' },
        { key: 'amount_eur', label: 'EUR', render: (r) => formatEur(r.payload?.transfer?.amount_eur) },
        {
          key: 'a', label: 'Action', render: (r) => r.status === 'PENDING_REVIEW' ? (
            <div className="flex gap-2">
              <button
                data-testid={`trp-accept-${r.id}`}
                onClick={() => decideTrp(r.id, 'ACCEPT')}
                className="text-xs px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20"
              >
                Accept
              </button>
              <button
                data-testid={`trp-reject-${r.id}`}
                onClick={() => decideTrp(r.id, 'REJECT')}
                className="text-xs px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20"
              >
                Reject
              </button>
            </div>
          ) : <span className="text-slate-600 text-xs">—</span>,
        },
      ]} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Root with route guard
// ────────────────────────────────────────────────────────────────────────
export default function Admin() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center bg-[#0a0f1c] text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login?redirect=/admin" replace />;
  if (user.role !== 'ADMIN') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#0a0f1c] text-slate-300 text-center px-6">
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-8 py-6 max-w-md">
          <div className="text-rose-300 font-semibold mb-2">Access denied</div>
          <p className="text-sm text-rose-200/80">
            The CASP back-office is restricted to ADMIN users. Your account ({user.email}) has role <code>{user.role}</code>.
          </p>
        </div>
      </div>
    );
  }
  return (
    <AdminLayout>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="setup" element={<SetupWizard />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="aml" element={<AmlPage />} />
        <Route path="treasury" element={<TreasuryPage />} />
        <Route path="otc" element={<OtcPage />} />
        <Route path="reporting" element={<ReportingPage />} />
        <Route path="protection" element={<ProtectionPage />} />
        <Route path="governance" element={<GovernancePage />} />
        <Route path="autonomy" element={<AutonomyPage />} />
        <Route path="audit" element={<AuditPage />} />
      </Routes>
      <AssistantWidget context="admin" />
    </AdminLayout>
  );
}
