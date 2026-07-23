import React, { useState } from 'react';
import { Beaker, Play, ArrowUpRight, ArrowDownRight, RefreshCw, Copy } from 'lucide-react';
import { TransakIframeModal } from '../transak/TransakIframeModal';

/**
 * Developer-facing Transak sandbox card.
 *
 * Lets a developer trigger the Transak iframe modal directly from the
 * Dev Portal to test the integration end-to-end without going through
 * the retail Dashboard KYC gate (DEVELOPER role bypasses the KYC gate
 * server-side per middleware/kyc_gate.py).
 */
export const TransakSandboxCard = () => {
  const [modal, setModal] = useState({ open: false, mode: 'BUY' });
  const [walletAddress, setWalletAddress] = useState('');

  const NENO_CONTRACT = '0xeF3F5C1892A8d7A3304E4A15959E124402d69974';

  const copy = (text) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text);
    }
  };

  return (
    <>
      <div
        className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-6"
        data-testid="devportal-transak-sandbox"
      >
        <div className="flex items-center gap-2 mb-4">
          <Beaker className="h-5 w-5 text-purple-300" />
          <h2 className="text-xl font-bold text-white">Transak Sandbox</h2>
          <span className="ml-auto text-[10px] uppercase tracking-wider text-purple-300 bg-purple-500/20 px-2 py-1 rounded">
            NENO · BSC · EUR
          </span>
        </div>

        <p className="text-sm text-gray-300 mb-4">
          Trigger the Transak Web widget in an iframe modal. Uses the same
          server-signed session URL that retail customers receive
          (<code className="font-mono text-purple-200">POST /api/transak/widget-url</code>).
          Developers bypass the KYC gate for integration testing.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              Test wallet address (optional)
            </label>
            <input
              type="text"
              value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
              placeholder="0x… (auto-detects if empty)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono"
              data-testid="devportal-transak-wallet-input"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              NENO contract (auto-injected)
            </label>
            <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2">
              <code className="text-xs text-purple-200 font-mono truncate flex-1">
                {NENO_CONTRACT}
              </code>
              <button
                onClick={() => copy(NENO_CONTRACT)}
                className="text-gray-400 hover:text-white"
                aria-label="Copy contract"
                data-testid="devportal-copy-contract"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <SandboxBtn
            onClick={() => setModal({ open: true, mode: 'BUY' })}
            color="from-emerald-600 to-emerald-500"
            Icon={ArrowUpRight}
            label="Launch Buy"
            testId="devportal-launch-buy"
          />
          <SandboxBtn
            onClick={() => setModal({ open: true, mode: 'SELL' })}
            color="from-rose-600 to-rose-500"
            Icon={ArrowDownRight}
            label="Launch Sell"
            testId="devportal-launch-sell"
          />
          <SandboxBtn
            onClick={() => setModal({ open: true, mode: 'SWAP' })}
            color="from-purple-600 to-purple-500"
            Icon={RefreshCw}
            label="Launch Swap"
            testId="devportal-launch-swap"
          />
        </div>

        <div className="mt-4 rounded-lg bg-slate-950/50 border border-white/5 p-3 text-xs text-gray-400 font-mono overflow-x-auto">
          <p className="text-purple-300 mb-1">Request body sent to /api/transak/widget-url:</p>
          {`{
  "productsAvailed": "BUY | SELL | BUY,SELL",
  "cryptoCurrencyCode": "NENO",
  "cryptoCurrencyAddress": "${NENO_CONTRACT}",
  "network": "bsc",
  "defaultFiatCurrency": "EUR",
  "themeColor": "7c3aed",
  "hideMenu": "true",
  "referrerDomain": "<your host>"
}`}
        </div>
      </div>

      <TransakIframeModal
        open={modal.open}
        onClose={() => setModal({ ...modal, open: false })}
        mode={modal.mode}
        walletAddress={walletAddress}
      />
    </>
  );
};

const SandboxBtn = ({ onClick, color, Icon, label, testId }) => (
  <button
    onClick={onClick}
    data-testid={testId}
    className={`rounded-xl bg-gradient-to-br ${color} p-4 text-white text-left hover:scale-[1.02] transition-transform`}
  >
    <Icon className="h-5 w-5 mb-2 opacity-90" />
    <div className="flex items-center gap-1">
      <Play className="h-3.5 w-3.5" />
      <span className="font-semibold text-sm">{label}</span>
    </div>
  </button>
);

export default TransakSandboxCard;
