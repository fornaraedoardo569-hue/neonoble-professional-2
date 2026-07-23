import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, RefreshCw, ShieldCheck, Lock } from 'lucide-react';

/**
 * Retail ramp CTA shown on the user Dashboard. Three call-to-actions
 * (Buy / Sell / Swap) routed to the public /transak page that hosts the
 * Transak widget launcher (server-side session API per the partner spec).
 *
 * The CTAs are visually disabled when KYC is not APPROVED — Transak still
 * enforces its own KYC, but we surface the requirement clearly so users
 * don't bounce off a half-finished onboarding.
 */
export const RetailRampCTA = ({ kycStatus }) => {
  const kycReady = kycStatus === 'APPROVED';

  const items = [
    { mode: 'BUY', label: 'Buy Crypto', color: 'from-emerald-600 to-emerald-500', Icon: ArrowUpRight, testId: 'retail-buy-cta' },
    { mode: 'SELL', label: 'Sell Crypto', color: 'from-rose-600 to-rose-500', Icon: ArrowDownRight, testId: 'retail-sell-cta' },
    { mode: 'SWAP', label: 'Swap', color: 'from-purple-600 to-purple-500', Icon: RefreshCw, testId: 'retail-swap-cta' },
  ];

  return (
    <div
      className="rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-900/20 to-slate-900/20 p-6"
      data-testid="retail-ramp-cta"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-purple-300" />
            Retail Ramp — non-custodial
          </h2>
          <p className="text-sm text-gray-300 mt-1 max-w-xl">
            Buy, sell or swap crypto directly to your own wallet via Transak.
            NeoNoble never touches the funds — settled directly between you,
            Transak and the network.
          </p>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-purple-300 bg-purple-500/20 px-2 py-1 rounded">
          Production
        </span>
      </div>

      {!kycReady && (
        <div
          className="mb-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 flex items-start gap-2 text-sm"
          data-testid="retail-ramp-kyc-gate"
        >
          <Lock className="h-4 w-4 text-yellow-300 mt-0.5 flex-shrink-0" />
          <div className="flex-1 text-yellow-100">
            <p className="font-medium">Complete identity verification first</p>
            <p className="text-yellow-200/70 text-xs mt-0.5">
              MiCAR &amp; AML rules require approved KYC before you can transact.
              {' '}
              <Link to="/onboarding" className="underline hover:text-yellow-50">Start now →</Link>
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map(({ mode, label, color, Icon, testId }) => (
          <Link
            key={mode}
            to={kycReady ? `/transak?mode=${mode}` : '/onboarding'}
            data-testid={testId}
            className={`relative group rounded-xl bg-gradient-to-br ${color} p-4 text-white shadow-lg ${
              kycReady ? 'hover:scale-[1.02]' : 'opacity-60 cursor-pointer'
            } transition-transform`}
          >
            <Icon className="h-5 w-5 mb-2 opacity-90" />
            <p className="font-semibold">{label}</p>
            <p className="text-xs opacity-80 mt-0.5">
              {mode === 'BUY' && 'Card / SEPA → crypto'}
              {mode === 'SELL' && 'Crypto → bank / card'}
              {mode === 'SWAP' && 'Crypto ↔ crypto'}
            </p>
          </Link>
        ))}
      </div>

      <p className="text-xs text-gray-500 mt-4">
        Powered by Transak (FinCEN-MSB &amp; FCA-registered) — single-use widget URL
        signed by NeoNoble's partner backend, expires in 5 minutes.
      </p>
    </div>
  );
};

export default RetailRampCTA;
