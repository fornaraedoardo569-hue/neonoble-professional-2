import React, { useEffect, useState } from 'react';
import { X, ChevronRight, ChevronLeft, Play, ShieldCheck, Wallet, FileText, AlertTriangle, CheckCircle2 } from 'lucide-react';

const STORAGE_KEY = 'neonoble_admin_walkthrough_seen_v1';

const STEPS = [
  {
    icon: Play,
    title: 'Benvenuto nella CASP Console',
    body: (
      <>
        <p>NeoNoble Ramp opera in <span className="text-emerald-300 font-semibold">modalità autonoma</span> sotto MiCAR — zero dipendenze da Sumsub, Chainalysis, Fireblocks o Notabene. Tutto è in-house.</p>
        <p className="mt-3 text-amber-300/80 text-sm">Questo tour ti accompagna nei 5 flussi self-service principali in ~2 minuti.</p>
      </>
    ),
  },
  {
    icon: ShieldCheck,
    title: '1. Onboarding cliente (KYC)',
    body: (
      <>
        <p>Vai su <code className="bg-slate-800 px-1 rounded">/admin/compliance</code> → tab <strong>KYC</strong> per vedere la coda di onboarding.</p>
        <p className="mt-2 text-sm text-slate-400">Per ogni richiesta in <code>IN_REVIEW</code>:</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400 list-disc list-inside">
          <li>Controlla i documenti caricati (KycRecord)</li>
          <li>Verifica lo sanctions screening interno</li>
          <li>Premi <span className="text-emerald-300">Approve</span> o <span className="text-rose-300">Reject</span></li>
        </ul>
        <p className="mt-3 text-xs text-slate-500">L'audit log registra automaticamente la tua decisione con firma hash-chained.</p>
      </>
    ),
  },
  {
    icon: AlertTriangle,
    title: '2. Review AML alerts',
    body: (
      <>
        <p>Su <code className="bg-slate-800 px-1 rounded">/admin/aml</code> trovi gli alert generati dal motore KYT interno.</p>
        <p className="mt-2 text-sm text-slate-400">Per alert <span className="text-rose-300">CRITICAL</span> (sanctioned address, mixer):</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400 list-disc list-inside">
          <li>Indaga la transazione</li>
          <li>Se confermato → bottone <strong>Escalate</strong></li>
          <li>Se falso positivo → bottone <strong>False+</strong></li>
          <li>Per casi gravi → genera un SAR draft (richiede MLRO)</li>
        </ul>
      </>
    ),
  },
  {
    icon: Wallet,
    title: '3. Proof-of-Reserves',
    body: (
      <>
        <p>Su <code className="bg-slate-800 px-1 rounded">/admin/treasury</code> clicca <strong>Generate PoR Snapshot</strong>.</p>
        <p className="mt-2 text-sm text-slate-400">Cosa fa:</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400 list-disc list-inside">
          <li>Legge i balance on-chain di ogni wallet registrato</li>
          <li>Calcola la Merkle root (CONSOB-grade evidence)</li>
          <li>Confronta totale assets vs liabilities (coverage ratio)</li>
          <li>Snapshot persistito nell'audit log</li>
        </ul>
        <p className="mt-3 text-xs text-amber-300/80">Raccomandato: genera un PoR ogni lunedì mattina.</p>
      </>
    ),
  },
  {
    icon: FileText,
    title: '4. Report MiCAR T+1',
    body: (
      <>
        <p>Su <code className="bg-slate-800 px-1 rounded">/admin/reporting</code> clicca <strong>Generate MiCAR Report</strong>.</p>
        <p className="mt-2 text-sm text-slate-400">Il report copre gli ultimi 30 giorni:</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400 list-disc list-inside">
          <li>Volumi OTC eseguiti</li>
          <li>Numero di SAR filed</li>
          <li>Capital adequacy snapshot</li>
        </ul>
        <p className="mt-3 text-xs text-slate-500">Pronto per upload portale CONSOB / Banca d'Italia.</p>
      </>
    ),
  },
  {
    icon: CheckCircle2,
    title: 'Sei pronto!',
    body: (
      <>
        <p>Hai visto il flusso completo. Le altre sezioni utili:</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-400 list-disc list-inside">
          <li><strong>OTC Desk B2B</strong> — ordini istituzionali con 4-eye &gt; €50k</li>
          <li><strong>Governance</strong> — RBAC, incidenti DORA, conflitti di interesse</li>
          <li><strong>Autonomy</strong> — KYT live tester + VASP directory + TRP inbox</li>
          <li><strong>Audit Log</strong> — verifica hash-chain on-demand</li>
        </ul>
        <p className="mt-4 text-xs text-emerald-300">💡 Puoi rilanciare questo tour in qualsiasi momento dalla Dashboard.</p>
      </>
    ),
  },
];

export default function AdminWalkthrough({ force, onClose }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (force) { setOpen(true); setStep(0); return; }
    if (typeof window !== 'undefined' && !window.localStorage.getItem(STORAGE_KEY)) {
      const t = setTimeout(() => setOpen(true), 800);
      return () => clearTimeout(t);
    }
  }, [force]);

  const dismiss = () => {
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setOpen(false);
    onClose?.();
  };

  if (!open) return null;
  const S = STEPS[step];
  const Icon = S.icon;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      data-testid="admin-walkthrough"
      onClick={(e) => { if (e.target === e.currentTarget) dismiss(); }}
    >
      <div className="relative w-full max-w-xl rounded-xl border border-amber-400/30 bg-[#0d1424] shadow-2xl">
        <button
          aria-label="Close"
          data-testid="walkthrough-close"
          onClick={dismiss}
          className="absolute top-3 right-3 text-slate-500 hover:text-slate-200"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="p-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-lg bg-amber-400/10 border border-amber-400/30 flex items-center justify-center">
              <Icon className="h-5 w-5 text-amber-300" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Step {step + 1} / {STEPS.length}</div>
              <h2 className="text-lg font-semibold text-slate-100">{S.title}</h2>
            </div>
          </div>
          <div className="text-slate-300 text-sm leading-relaxed min-h-[180px]">{S.body}</div>

          {/* Progress dots */}
          <div className="flex justify-center gap-1.5 mt-6">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all ${i === step ? 'w-6 bg-amber-300' : i < step ? 'w-1.5 bg-amber-400/40' : 'w-1.5 bg-slate-700'}`}
              />
            ))}
          </div>

          <div className="flex items-center justify-between mt-6">
            <button
              data-testid="walkthrough-prev"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="px-3 py-1.5 rounded text-sm text-slate-400 hover:text-slate-200 disabled:opacity-30 inline-flex items-center gap-1"
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <button
              data-testid="walkthrough-skip"
              onClick={dismiss}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              Skip tour
            </button>
            {step < STEPS.length - 1 ? (
              <button
                data-testid="walkthrough-next"
                onClick={() => setStep((s) => s + 1)}
                className="px-4 py-1.5 rounded bg-amber-400/10 text-amber-300 border border-amber-400/30 hover:bg-amber-400/20 text-sm inline-flex items-center gap-1"
              >
                Next <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                data-testid="walkthrough-finish"
                onClick={dismiss}
                className="px-4 py-1.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 text-sm"
              >
                Finish 🎉
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
