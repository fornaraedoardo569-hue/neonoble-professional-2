import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import api from '../../api';
import { transakApi } from '../../api/transak';

const STG_ORIGIN = 'https://global-stg.transak.com';
const PROD_ORIGIN = 'https://global.transak.com';
const POPUP_FEATURES =
  'width=480,height=720,resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no,location=no';

const PRODUCT_MAP = { BUY: 'BUY', SELL: 'SELL', SWAP: 'BUY,SELL' };

const TRACKED_EVENT_PREFIX = 'TRANSAK_';

const buildClientParams = (config, walletAddress, productsAvailed, token) => {
  // The backend enforces apiKey + referrerDomain — we still send referrerDomain
  // as a hint (window.location.host) so the backend has it.
  const liveReferrer =
    typeof window !== 'undefined' && window.location?.host
      ? window.location.host
      : config?.referrer_domain || '';
  return {
    productsAvailed,
    cryptoCurrencyCode: token.code,
    network: token.network,
    walletAddress,
    disableWalletAddressForm: 'true',
    hideMenu: 'true',
    themeColor: '7c3aed',
    defaultFiatCurrency: config?.fiat_currency || 'EUR',
    referrerDomain: liveReferrer,
    partnerCustomerId: walletAddress,
  };
};

export const TransakLauncher = ({ config, walletAddress, isBSC, onEvent }) => {
  const catalogue = useMemo(() => config?.catalogue || [], [config]);
  const defaultToken = useMemo(() => {
    if (!catalogue.length) {
      return {
        code: config?.supports_neno ? 'NENO' : config?.fallback_token || 'USDC',
        network: 'bsc',
        label: '',
      };
    }
    return catalogue[0];
  }, [catalogue, config]);

  const [selectedToken, setSelectedToken] = useState(defaultToken);
  const [opening, setOpening] = useState(null);
  const [lastEvent, setLastEvent] = useState(null);
  const [launchError, setLaunchError] = useState('');

  const popupRef = useRef(null);
  const pollRef = useRef(null);
  const allowedOriginRef = useRef(STG_ORIGIN);

  useEffect(() => {
    setSelectedToken(defaultToken);
  }, [defaultToken]);

  useEffect(() => {
    const handler = (event) => {
      if (event.origin !== allowedOriginRef.current) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      const name = data.event_id || data.eventName || data.type;
      if (!name || typeof name !== 'string' || !name.startsWith(TRACKED_EVENT_PREFIX)) return;
      setLastEvent({ name, at: new Date().toISOString() });
      onEvent?.(name, data);
      transakApi.logEvent(walletAddress, name, data).catch(() => {});
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [walletAddress, onEvent]);

  const startCloseWatcher = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => {
      if (!popupRef.current || popupRef.current.closed) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        if (popupRef.current) {
          const name = 'TRANSAK_WIDGET_CLOSE';
          setLastEvent({ name, at: new Date().toISOString() });
          onEvent?.(name, { reason: 'popup_closed' });
          transakApi.logEvent(walletAddress, name, { reason: 'popup_closed' }).catch(() => {});
        }
        popupRef.current = null;
        setOpening(null);
      }
    }, 600);
  }, [walletAddress, onEvent]);

  useEffect(
    () => () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (popupRef.current && !popupRef.current.closed) {
        try { popupRef.current.close(); } catch (_) {}
      }
    },
    []
  );

  const launch = useCallback(
    async (mode) => {
      if (!walletAddress || !selectedToken) return;
      setOpening(mode);
      setLaunchError('');
      allowedOriginRef.current =
        config.environment === 'PRODUCTION' ? PROD_ORIGIN : STG_ORIGIN;

      const params = buildClientParams(config, walletAddress, PRODUCT_MAP[mode], selectedToken);
      let widgetUrl = '';
      try {
        const { data } = await api.post('/transak/widget-url', params);
        widgetUrl = data?.widget_url || '';
      } catch (err) {
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail || err?.message || 'Failed to create Transak widget URL';
        let msg = detail;
        if (status === 409 && String(detail).includes('TRANSAK_KYB_PENDING')) {
          msg = 'Transak account approval pending — we have valid Production credentials but Transak compliance has not yet activated widget session creation for this account. Please retry in a few hours, or contact NeoNoble support if this persists.';
        }
        setLaunchError(msg);
        setOpening(null);
        return;
      }
      if (!widgetUrl) {
        setLaunchError('Transak returned an empty widget URL. Try again.');
        setOpening(null);
        return;
      }

      if (popupRef.current && !popupRef.current.closed) {
        try {
          popupRef.current.location.replace(widgetUrl);
          popupRef.current.focus();
          return;
        } catch (_) {
          try { popupRef.current.close(); } catch (_) {}
        }
      }

      const popup = window.open(widgetUrl, 'transak-widget', POPUP_FEATURES);
      if (!popup) {
        window.location.href = widgetUrl;
        return;
      }
      popupRef.current = popup;
      try { popup.focus(); } catch (_) {}
      startCloseWatcher();

      const name = 'TRANSAK_WIDGET_LAUNCHED';
      setLastEvent({ name, at: new Date().toISOString() });
      onEvent?.(name, { mode, token: selectedToken });
      transakApi
        .logEvent(walletAddress, name, { mode, token: selectedToken })
        .catch(() => {});
    },
    [config, walletAddress, selectedToken, onEvent, startCloseWatcher]
  );

  const isBscToken = selectedToken?.network === 'bsc';
  const disabled = !walletAddress || (isBscToken && !isBSC);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6" data-testid="transak-launcher">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-white text-lg font-semibold">Step 2 — Trade through Transak</h2>
        <span className="text-xs text-purple-300 uppercase tracking-wider">
          {config?.environment}
        </span>
      </div>

      <p className="text-gray-300 text-sm mb-3">
        Token:{' '}
        <span className="font-mono text-purple-200" data-testid="selected-token-label">
          {selectedToken?.label || `${selectedToken?.code} · ${selectedToken?.network?.toUpperCase()}`}
        </span>{' '}
        — fiat: <span className="font-mono text-purple-200">{config?.fiat_currency || 'EUR'}</span>
      </p>

      <div className="mb-4">
        <label className="block text-xs text-gray-400 mb-2">Pick a token</label>
        <div className="flex flex-wrap gap-2" data-testid="token-picker">
          {catalogue.map((token) => {
            const isSelected =
              selectedToken &&
              selectedToken.code === token.code &&
              selectedToken.network === token.network;
            return (
              <button
                key={`${token.code}-${token.network}`}
                onClick={() => setSelectedToken(token)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  isSelected
                    ? 'bg-purple-600 border-purple-500 text-white'
                    : 'bg-white/5 border-white/10 text-gray-300 hover:bg-white/10'
                }`}
                data-testid={`token-${token.code}-${token.network}`}
              >
                {token.label}
              </button>
            );
          })}
        </div>
        {!config?.supports_neno && (
          <p className="text-xs text-yellow-300/80 mt-2" data-testid="neno-pending-note">
            NENO listing on Transak is pending — file an "Add Custom Token" request in the Transak
            Partner Dashboard with the contract{' '}
            <span className="font-mono">{config?.neno_contract?.slice(0, 10)}…</span>.
          </p>
        )}
      </div>

      <div className="flex items-start gap-2 text-xs text-gray-400 mb-5">
        <ExternalLink className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-purple-300" />
        <p>
          Transak opens in a separate popup window via a server-side session URL — never an iframe.
          walletAddress is locked to the address you connected above
          (<code>disableWalletAddressForm=true</code>).
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <LaunchButton
          label="Buy Crypto"
          icon={<ArrowUpRight className="h-4 w-4" />}
          color="bg-emerald-600 hover:bg-emerald-700"
          loading={opening === 'BUY'}
          disabled={disabled}
          onClick={() => launch('BUY')}
          testId="launch-buy-btn"
        />
        <LaunchButton
          label="Sell Crypto"
          icon={<ArrowDownRight className="h-4 w-4" />}
          color="bg-rose-600 hover:bg-rose-700"
          loading={opening === 'SELL'}
          disabled={disabled}
          onClick={() => launch('SELL')}
          testId="launch-sell-btn"
        />
        <LaunchButton
          label="Swap (Buy/Sell)"
          icon={<RefreshCw className="h-4 w-4" />}
          color="bg-purple-600 hover:bg-purple-700"
          loading={opening === 'SWAP'}
          disabled={disabled}
          onClick={() => launch('SWAP')}
          testId="launch-swap-btn"
        />
      </div>

      {launchError && (
        <div
          className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-red-200 text-xs"
          data-testid="launch-error"
        >
          {launchError}
        </div>
      )}

      {disabled && (
        <p className="text-yellow-300 text-xs mt-4" data-testid="launcher-disabled-note">
          {walletAddress
            ? 'Switch your wallet to BNB Smart Chain to trade this BSC token.'
            : 'Connect your wallet first to enable Buy/Sell/Swap.'}
        </p>
      )}

      {lastEvent && (
        <div
          className="mt-5 rounded-lg border border-white/5 bg-black/20 px-3 py-2 text-xs text-gray-300"
          data-testid="last-event"
        >
          Last Transak event:{' '}
          <span className="font-mono text-purple-200">{lastEvent.name}</span>{' '}
          <span className="text-gray-500">@ {new Date(lastEvent.at).toLocaleTimeString()}</span>
        </div>
      )}

      <details className="mt-3 text-xs text-gray-400" data-testid="referrer-diagnostic">
        <summary className="cursor-pointer hover:text-gray-300">
          Referrer diagnostic (use this if Transak rejects the session)
        </summary>
        <div className="mt-2 rounded-lg bg-black/30 p-3 space-y-1 font-mono text-[11px]">
          <p>
            referrerDomain sent:{' '}
            <span className="text-purple-200">
              {typeof window !== 'undefined' ? window.location.host : '(unknown)'}
            </span>
          </p>
          <p>
            apiKey prefix:{' '}
            <span className="text-purple-200">
              {(config?.api_key || '').slice(0, 8)}…
            </span>
          </p>
          <p>
            environment: <span className="text-purple-200">{config?.environment}</span>
          </p>
          <p className="text-gray-500 mt-2">
            If Buy/Sell fails: in the Transak Partner Dashboard, confirm both the{' '}
            <strong>referrer domain above</strong> AND the IP of this backend are whitelisted.
          </p>
        </div>
      </details>
    </div>
  );
};

const LaunchButton = ({ label, icon, color, loading, disabled, onClick, testId }) => (
  <button
    onClick={onClick}
    disabled={disabled || loading}
    className={`${color} disabled:opacity-40 text-white px-4 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all`}
    data-testid={testId}
  >
    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
    <span>{loading ? 'Opening…' : label}</span>
  </button>
);
