import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, RefreshCw, ShieldCheck, Lock, Coins } from 'lucide-react';
import { TransakIframeModal } from '../transak/TransakIframeModal';

/**
 * StartTradingCard — top-of-dashboard "Start Trading" workflow.
 *
 * A KYC-gated card exposing three CTAs (Buy / Sell / Swap) that open the
 * Transak widget inside a responsive iframe modal — no popup, no page
 * navigation. Widget params are configured server-side to target NENO on
 * BSC by default (contract 0xeF3F...9974) with EUR as the fiat currency.
 *
 * If KYC is not APPROVED, the CTAs redirect to /onboarding instead.
 */
export const StartTradingCard = ({ kycStatus, walletAddress = '' }) => {
  const [modalState, setModalState] = useState({ open: false, mode: 'BUY' });
  const kycReady = kycStatus === 'APPROVED';

  const openMode = (mode) => {
    if (!kycReady) return;
    setModalState({ open: true, mode });
  };

  const items = [
    { mode: 'BUY', label: 'Buy Crypto', desc: 'Card / SEPA → NENO', color: 'from-emerald-600 to-emerald-500', Icon: ArrowUpRight, testId: 'start-trading-buy' },
    { mode: 'SELL', label: 'Sell Crypto', desc: 'NENO → bank / card', color: 'from-rose-600 to-rose-500', Icon: ArrowDownRight, testId: 'start-trading-sell' },
    { mode: 'SWAP', label: 'Swap', desc: 'Crypto ↔ crypto', color: 'from-purple-600 to-purple-500', Icon: RefreshCw, testId: 'start-trading-swap' },
  ];

  return (
    <>
      <div
        className="rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-900/25 to-slate-900/25 p-6"
        data-testid="start-trading-card"
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Coins className="h-5 w-5 text-purple-300" />
              Start Trading
            </h2>
            <p className="text-sm text-gray-300 mt-1 max-w-xl">
              Buy, sell or swap crypto directly to your own wallet via Transak.
              Default target is <span className="font-mono text-purple-200">NENO</span>{' '}
              on Binance Smart Chain — settle in EUR without leaving this page.
            </p>
          </div>
          <span className="text-[10px] uppercase tracking-wider text-purple-300 bg-purple-500/20 px-2 py-1 rounded">
            BSC · EUR
          </span>
        </div>

        {!kycReady && (
          <div
            className="mb-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 flex items-start gap-2 text-sm"
            data-testid="start-trading-kyc-gate"
          >
            <Lock className="h-4 w-4 text-yellow-300 mt-0.5 flex-shrink-0" />
            <div className="flex-1 text-yellow-100">
              <p className="font-medium">Identity verification required</p>
              <p className="text-yellow-200/70 text-xs mt-0.5">
                MiCAR &amp; AML rules require approved KYC.
                {' '}
                <Link to="/onboarding" className="underline hover:text-yellow-50">Complete now →</Link>
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {items.map(({ mode, label, desc, color, Icon, testId }) =>
            kycReady ? (
              <button
                key={mode}
                onClick={() => openMode(mode)}
                data-testid={testId}
                className={`text-left rounded-xl bg-gradient-to-br ${color} p-4 text-white shadow-lg hover:scale-[1.02] transition-transform focus:outline-none focus:ring-2 focus:ring-white/40`}
              >
                <Icon className="h-5 w-5 mb-2 opacity-90" />
                <p className="font-semibold">{label}</p>
                <p className="text-xs opacity-80 mt-0.5">{desc}</p>
              </button>
            ) : (
              <Link
                key={mode}
                to="/onboarding"
                data-testid={testId}
                className={`rounded-xl bg-gradient-to-br ${color} p-4 text-white shadow-lg opacity-60 cursor-pointer transition-opacity`}
              >
                <Icon className="h-5 w-5 mb-2 opacity-90" />
                <p className="font-semibold">{label}</p>
                <p className="text-xs opacity-80 mt-0.5">{desc}</p>
              </Link>
            )
          )}
        </div>

        <p className="text-xs text-gray-500 mt-4 flex items-center gap-1.5">
          <ShieldCheck className="h-3 w-3" />
          Powered by Transak · single-use widget URL signed by NeoNoble&apos;s partner backend
          (expires in 5 min). We never touch your funds.
        </p>
      </div>

      <TransakIframeModal
        open={modalState.open}
        onClose={() => setModalState({ ...modalState, open: false })}
        mode={modalState.mode}
        walletAddress={walletAddress}
      />
    </>
  );
};

export default StartTradingCard;
