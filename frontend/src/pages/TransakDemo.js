import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Coins, LogOut, ArrowLeft, ListChecks } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWallet } from '../hooks/useWallet';
import { transakApi } from '../api/transak';
import { ComplianceBanner } from '../components/transak/ComplianceBanner';
import { WalletConnect } from '../components/transak/WalletConnect';
import { TransakLauncher } from '../components/transak/TransakLauncher';
import { PancakeSwapPanel } from '../components/transak/PancakeSwapPanel';

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

export default function TransakDemo() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const wallet = useWallet();

  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState('');
  const [eventLog, setEventLog] = useState([]);

  useEffect(() => {
    transakApi
      .getConfig()
      .then(setConfig)
      .catch((err) => {
        devError('Failed to load Transak config:', err);
        setConfigError(err.response?.data?.detail || 'Failed to load Transak config');
      });
  }, []);

  const handleEvent = (name, data) => {
    setEventLog((prev) => [
      { name, data, at: new Date().toISOString() },
      ...prev.slice(0, 19),
    ]);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="transak-demo">
      <header className="border-b border-white/10 backdrop-blur-lg">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-2">
              <Coins className="h-8 w-8 text-purple-400" />
              <span className="text-xl font-bold text-white">NeoNoble Ramp</span>
              <span className="bg-purple-600 text-white text-xs px-2 py-1 rounded ml-2">
                Transak Demo
              </span>
            </Link>
            <div className="flex items-center space-x-4">
              <Link
                to="/dashboard"
                className="text-gray-300 hover:text-white px-3 py-2 text-sm inline-flex items-center gap-1"
                data-testid="back-to-dashboard"
              >
                <ArrowLeft className="h-4 w-4" /> Dashboard
              </Link>
              {user && (
                <>
                  <span className="text-gray-400 text-sm">{user.email}</span>
                  <button
                    onClick={handleLogout}
                    className="text-gray-400 hover:text-white p-2"
                    data-testid="logout-btn"
                  >
                    <LogOut className="h-5 w-5" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            On-Ramp · Off-Ramp · Swap via Transak
          </h1>
          <p className="text-gray-300 mt-2 max-w-2xl">
            This is the page used to record the UK-compliance walkthrough for Transak. It
            demonstrates a fully <span className="text-purple-200 font-medium">non-custodial</span>{' '}
            on-ramp / off-ramp / swap flow targeting the NENO token on BSC, with USDC as
            staging-time fallback until NENO is whitelisted on Transak staging.
          </p>
        </div>

        <ComplianceBanner />

        {configError && (
          <div
            className="rounded-2xl border border-red-500/40 bg-red-500/10 p-5 text-red-200"
            data-testid="config-error"
          >
            {configError}
          </div>
        )}

        <WalletConnect
          address={wallet.address}
          isBSC={wallet.isBSC}
          hasInjectedWallet={wallet.hasInjectedWallet}
          connecting={wallet.connecting}
          error={wallet.error}
          onConnect={wallet.connect}
          onSwitchBSC={wallet.switchToBSC}
        />

        {config && (
          <TransakLauncher
            config={config}
            walletAddress={wallet.address}
            isBSC={wallet.isBSC}
            onEvent={handleEvent}
          />
        )}

        {config && (
          <PancakeSwapPanel
            walletAddress={wallet.address}
            isBSC={wallet.isBSC}
            nenoContract={config.neno_contract}
          />
        )}

        {eventLog.length > 0 && (
          <div
            className="rounded-2xl border border-white/10 bg-white/5 p-6"
            data-testid="event-log"
          >
            <div className="flex items-center gap-2 mb-3">
              <ListChecks className="h-4 w-4 text-purple-300" />
              <h3 className="text-white font-semibold">Transak event stream</h3>
              <span className="text-xs text-gray-500 ml-auto">
                {eventLog.length} most recent
              </span>
            </div>
            <ul className="space-y-1 text-xs font-mono text-gray-300 max-h-64 overflow-auto">
              {eventLog.map((evt, idx) => (
                <li key={idx} className="border-b border-white/5 pb-1">
                  <span className="text-purple-200">{evt.name}</span>{' '}
                  <span className="text-gray-500">
                    {new Date(evt.at).toLocaleTimeString()}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {config && (
          <ConfigSummary config={config} />
        )}
      </div>
    </div>
  );
}

const ConfigSummary = ({ config }) => (
  <details
    className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-gray-300"
    data-testid="config-summary"
  >
    <summary className="cursor-pointer text-white font-semibold">
      Widget configuration (read-only)
    </summary>
    <pre className="mt-3 bg-black/30 rounded-lg p-4 text-xs text-purple-100 overflow-auto">
{JSON.stringify(config, null, 2)}
    </pre>
  </details>
);
