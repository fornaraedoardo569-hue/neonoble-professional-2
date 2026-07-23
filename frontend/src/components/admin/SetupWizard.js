import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, ShieldAlert, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { caspApi } from '../../api';
import { SectionHeader, Pill, Card, formatDateTime } from './ui';

const ENV_LABELS = {
  CASP_LIVE_MODE: 'Live mode flag',
  CASP_AUTONOMOUS_MODE: 'Autonomous adapters',
  TRANSAK_LIVE: 'Transak Production keys',
  STRIPE_LIVE: 'Stripe live SEPA payouts',
  TRP_SIGNING_SECRET_SET: 'TRP signing secret rotated',
  NEONOBLE_VASP_DID: 'NeoNoble VASP DID',
};

export default function SetupWizard() {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [form, setForm] = useState({
    legal_name: 'NeoNoble Technology Incorporation Limited',
    license_number: '',
    license_authority: 'CONSOB',
    license_valid_until: '',
    registered_address: '',
    vat_number: '',
    lei: '',
    contact_email: '',
    contact_phone: '',
    mlro_name: '',
  });

  const reload = async () => {
    try {
      const s = await caspApi.setupStatus();
      setStatus(s);
      if (s.config?.legal_entity) {
        setForm((f) => ({ ...f, ...s.config.legal_entity }));
      }
    } catch (e) {
      toast.error('Failed to load setup status');
    }
  };
  useEffect(() => { reload(); }, []);

  const saveLegalEntity = async () => {
    if (!form.license_number || !form.contact_email || !form.license_valid_until) {
      toast.error('License #, contact email and valid-until are required');
      return;
    }
    try {
      await caspApi.setupLegalEntity(form);
      toast.success('Legal entity recorded — pinned in audit log');
      reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    }
  };

  if (!status) return <div className="text-slate-400">Loading setup status…</div>;

  const StepRow = ({ s }) => (
    <li className={`flex items-start gap-3 rounded-md border p-3 ${s.done ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-800 bg-slate-900/40'}`}>
      {s.done
        ? <CheckCircle2 className="h-5 w-5 text-emerald-400 mt-0.5 flex-shrink-0" />
        : <Circle className="h-5 w-5 text-slate-600 mt-0.5 flex-shrink-0" />}
      <div className="flex-1">
        <div className="text-sm font-medium text-slate-100">
          {s.id}. {s.title} {s.done && <Pill tone="green">DONE</Pill>}
        </div>
        <div className="text-xs text-slate-400 mt-0.5">{s.details}</div>
      </div>
    </li>
  );

  return (
    <div data-testid="admin-setup-wizard">
      <SectionHeader
        title="Real Mode Setup Wizard"
        subtitle="5-step path from demo to fully operational CASP. The platform completed everything technical; remaining steps require your legal-entity signature."
        actions={<Pill tone={status.completeness_pct === 100 ? 'green' : 'yellow'}>
          {status.completeness_pct}% complete
        </Pill>}
      />

      {/* Progress overview */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5 mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Onboarding checklist</h2>
          {status.live_mode && <Pill tone="green">LIVE MODE</Pill>}
        </div>
        <ul className="space-y-2">
          {status.steps.map((s) => <StepRow key={s.id} s={s} />)}
        </ul>
      </div>

      {/* Environment flags */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5 mb-6">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Environment flags</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          {Object.entries(status.env_flags).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between rounded border border-slate-800 px-3 py-2">
              <span className="text-slate-400">{ENV_LABELS[k] || k}</span>
              {typeof v === 'boolean'
                ? <Pill tone={v ? 'green' : 'red'}>{v ? 'ON' : 'OFF'}</Pill>
                : <code className="text-xs text-slate-300 truncate max-w-[200px]" title={v}>{v || '—'}</code>}
            </div>
          ))}
        </div>
      </div>

      {/* Step 2: Legal entity form */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5 mb-6" data-testid="legal-entity-form">
        <h2 className="text-sm font-semibold text-slate-200 mb-1">Step 2 — Legal entity & CASP license</h2>
        <p className="text-xs text-slate-500 mb-4">Recorded in audit log. Required by CONSOB and shown on every regulatory report.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <input placeholder="Legal name" value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 md:col-span-2" />
          <input placeholder="CASP license number" value={form.license_number} onChange={(e) => setForm({ ...form, license_number: e.target.value })} className="bg-slate-900 border border-amber-500/30 rounded px-3 py-1.5" />
          <input placeholder="License authority (CONSOB / Banca d'Italia)" value={form.license_authority} onChange={(e) => setForm({ ...form, license_authority: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5" />
          <input type="date" placeholder="Valid until" value={form.license_valid_until} onChange={(e) => setForm({ ...form, license_valid_until: e.target.value })} className="bg-slate-900 border border-amber-500/30 rounded px-3 py-1.5" />
          <input placeholder="LEI (optional)" value={form.lei} onChange={(e) => setForm({ ...form, lei: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5" />
          <input placeholder="Registered address" value={form.registered_address} onChange={(e) => setForm({ ...form, registered_address: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 md:col-span-2" />
          <input placeholder="VAT number" value={form.vat_number} onChange={(e) => setForm({ ...form, vat_number: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5" />
          <input placeholder="Contact email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} className="bg-slate-900 border border-amber-500/30 rounded px-3 py-1.5" />
          <input placeholder="MLRO full name" value={form.mlro_name} onChange={(e) => setForm({ ...form, mlro_name: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5" />
          <input placeholder="Contact phone" value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5" />
        </div>
        <div className="mt-3 flex justify-end">
          <button data-testid="legal-entity-save" onClick={saveLegalEntity} className="px-3 py-1.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 text-sm">
            Save Legal Entity
          </button>
        </div>
      </div>

      {/* Step 3 + 5: Direct deep-link */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-5 mb-6">
        <div className="flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-amber-200 mb-2">Steps 3 & 5 — Actions only you can sign</h2>
            <ul className="text-sm text-amber-100/80 space-y-3">
              <li>
                <strong>Step 3 — Capital adequacy</strong>: open <button onClick={() => navigate('/admin/reporting')} className="underline">Reporting</button> and post a snapshot with your real own-funds value (audited figure from CFO). MiCAR Class 2 requires ≥ €125 000.
              </li>
              <li>
                <strong>Step 5 — Transak Production keys</strong>: reply to Rahul Das from your inbox using <code>/app/TRANSAK_COMPLIANCE_REPLY.md</code>. Once he confirms KYB approval, paste the production API key + secret into <code>/app/backend/.env</code> as <code>TRANSAK_API_KEY</code> and <code>TRANSAK_API_SECRET</code>, set <code>TRANSAK_ENV=PRODUCTION</code>, restart backend.
                <a className="ml-2 inline-flex items-center gap-1 underline" href="https://dashboard.transak.com" target="_blank" rel="noreferrer">
                  Transak dashboard <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="Custodial wallets" value={status.data_counts.wallets} hint="Register real wallets in Treasury" />
        <Card title="Approved KYC" value={status.data_counts.kyc_approved} hint="Onboard first real client" />
        <Card title="Peer VASPs" value={status.data_counts.peer_vasps} hint="Add via Autonomy tab" />
      </div>
    </div>
  );
}
