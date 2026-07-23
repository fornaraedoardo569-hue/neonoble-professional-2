import React from 'react';
import { Wallet, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';

const shorten = (addr) => (addr ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : '');

export const WalletConnect = ({
  address,
  isBSC,
  hasInjectedWallet,
  connecting,
  error,
  onConnect,
  onSwitchBSC,
}) => {
  if (!hasInjectedWallet) {
    return (
      <div
        className="rounded-2xl border border-yellow-500/30 bg-yellow-500/10 p-5"
        data-testid="wallet-no-injected"
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-300 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-yellow-100 font-semibold">No browser wallet detected</p>
            <p className="text-yellow-200/80 text-sm mt-1">
              Install{' '}
              <a
                href="https://metamask.io/download/"
                target="_blank"
                rel="noreferrer"
                className="underline"
              >
                MetaMask
              </a>{' '}
              (or any EIP-1193 wallet) to continue. NeoNoble never holds your keys — you sign every
              transaction yourself.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!address) {
    return (
      <div
        className="rounded-2xl border border-white/10 bg-white/5 p-5"
        data-testid="wallet-disconnected"
      >
        <div className="flex items-start gap-3 mb-4">
          <Wallet className="h-5 w-5 text-purple-300 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-white font-semibold">Step 1 — Connect your own wallet</p>
            <p className="text-gray-300 text-sm mt-1">
              The address you connect here is the <strong>only</strong> destination crypto will be
              delivered to. NeoNoble cannot move funds on your behalf.
            </p>
          </div>
        </div>
        <button
          onClick={onConnect}
          disabled={connecting}
          className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white px-5 py-2.5 rounded-xl font-semibold flex items-center gap-2"
          data-testid="connect-wallet-btn"
        >
          {connecting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wallet className="h-4 w-4" />}
          <span>{connecting ? 'Awaiting wallet…' : 'Connect Wallet'}</span>
        </button>
        {error && (
          <p className="text-red-300 text-sm mt-3" data-testid="wallet-error">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl border border-green-500/30 bg-green-500/10 p-5"
      data-testid="wallet-connected"
    >
      <div className="flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-300 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-green-100 font-semibold">Wallet connected</p>
          <p
            className="text-green-200 text-sm font-mono mt-1 break-all"
            data-testid="wallet-address"
          >
            {address}
          </p>
          <p className="text-green-200/80 text-xs mt-2">
            Short: <span className="font-mono">{shorten(address)}</span> — this address is sent
            verbatim to Transak as <code>walletAddress</code>.
          </p>
          {!isBSC && (
            <button
              onClick={onSwitchBSC}
              className="mt-3 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-400/40 text-yellow-100 px-3 py-1.5 rounded-lg text-sm font-medium"
              data-testid="switch-bsc-btn"
            >
              Switch to BNB Smart Chain
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
