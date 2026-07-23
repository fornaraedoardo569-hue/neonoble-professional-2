import React, { useEffect, useRef, useState, useCallback } from 'react';
import { X, Loader2, AlertTriangle, ExternalLink, ShieldCheck } from 'lucide-react';
import api from '../../api';
import { transakApi } from '../../api/transak';

const STG_ORIGIN = 'https://global-stg.transak.com';
const PROD_ORIGIN = 'https://global.transak.com';
const TRACKED_EVENT_PREFIX = 'TRANSAK_';

// Product mapping for the Transak widget:
//   BUY  -> onramp only (fiat -> crypto)
//   SELL -> offramp only (crypto -> fiat)
//   SWAP -> BUY,SELL (Transak treats swap as multi-product ramp)
const PRODUCT_MAP = { BUY: 'BUY', SELL: 'SELL', SWAP: 'BUY,SELL' };

const MODE_LABEL = {
  BUY: 'Buy Crypto',
  SELL: 'Sell Crypto',
  SWAP: 'Swap Crypto',
};

/**
 * TransakIframeModal
 * ------------------
 * Responsive iframe modal (not popup) that hosts the Transak widget after
 * fetching a server-signed session URL from `/api/transak/widget-url`.
 *
 * Props:
 *   open (bool)             — whether the modal is visible
 *   onClose (fn)            — invoked when user closes the modal
 *   mode ('BUY'|'SELL'|'SWAP')
 *   walletAddress (string?) — pre-filled wallet address (optional)
 *   token ({code,network,contractAddress?}?) — token to target
 *                             defaults to NENO on BSC with the canonical
 *                             contract address
 *   onEvent (fn?)           — receives (eventName, payload) for every
 *                             Transak postMessage event
 */
export const TransakIframeModal = ({
  open,
  onClose,
  mode = 'BUY',
  walletAddress = '',
  token,
  onEvent,
}) => {
  const [config, setConfig] = useState(null);
  const [widgetUrl, setWidgetUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastEvent, setLastEvent] = useState(null);
  const iframeRef = useRef(null);
  const allowedOriginRef = useRef(STG_ORIGIN);

  // Fetch public config once
  useEffect(() => {
    if (!open || config) return;
    transakApi
      .getConfig()
      .then((c) => {
        setConfig(c);
        allowedOriginRef.current = c.environment === 'PRODUCTION' ? PROD_ORIGIN : STG_ORIGIN;
      })
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load Transak config'));
  }, [open, config]);

  // Handle Transak postMessage events (iframe -> parent)
  useEffect(() => {
    if (!open) return;
    const handler = (event) => {
      if (event.origin !== allowedOriginRef.current) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      const name = data.event_id || data.eventName || data.type;
      if (!name || typeof name !== 'string' || !name.startsWith(TRACKED_EVENT_PREFIX)) return;
      setLastEvent({ name, at: new Date().toISOString() });
      onEvent?.(name, data);
      if (walletAddress) {
        transakApi.logEvent(walletAddress, name, data).catch(() => {});
      }
      // Auto-close on final states
      if (
        name === 'TRANSAK_ORDER_SUCCESSFUL' ||
        name === 'TRANSAK_ORDER_CANCELLED' ||
        name === 'TRANSAK_WIDGET_CLOSE'
      ) {
        setTimeout(() => onClose?.(), 600);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [open, walletAddress, onEvent, onClose]);

  // Create the widget session URL when modal opens with a valid config
  useEffect(() => {
    if (!open || !config) return;

    setError('');
    setWidgetUrl('');
    setLoading(true);

    // Default token = NENO on BSC (contract enforced server-side)
    const targetToken =
      token || {
        code: 'NENO',
        network: 'bsc',
        contractAddress: config.neno_contract,
      };

    const params = {
      productsAvailed: PRODUCT_MAP[mode] || 'BUY',
      cryptoCurrencyCode: targetToken.code,
      network: targetToken.network || 'bsc',
      // The custom-token contract for NENO on BSC
      cryptoCurrencyAddress:
        targetToken.contractAddress || (targetToken.code === 'NENO' ? config.neno_contract : undefined),
      defaultFiatCurrency: config.fiat_currency || 'EUR',
      fiatCurrency: config.fiat_currency || 'EUR',
      themeColor: '7c3aed',
      hideMenu: 'true',
      referrerDomain: typeof window !== 'undefined' ? window.location.host : config.referrer_domain,
      partnerCustomerId: walletAddress || undefined,
    };
    if (walletAddress) {
      params.walletAddress = walletAddress;
      params.disableWalletAddressForm = 'true';
    }

    api
      .post('/transak/widget-url', params)
      .then(({ data }) => {
        setWidgetUrl(data?.widget_url || '');
        setLoading(false);
      })
      .catch((err) => {
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail || err?.message || 'Failed to create Transak widget URL';
        let msg = detail;
        if (typeof detail === 'string' && detail.includes('TRANSAK_KYB_PENDING')) {
          msg =
            'Transak account KYB is pending. Our Production credentials are valid — Transak Compliance will activate widget sessions shortly. Please try again later.';
        } else if (status === 403) {
          msg = 'Complete KYC verification before trading.';
        } else if (typeof detail === 'object') {
          msg = detail.message || JSON.stringify(detail);
        }
        setError(msg);
        setLoading(false);
      });
  }, [open, config, mode, walletAddress, token]);

  const handleClose = useCallback(() => {
    setWidgetUrl('');
    setLastEvent(null);
    setError('');
    onClose?.();
  }, [onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-2 sm:p-6"
      data-testid="transak-iframe-modal"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="relative w-full h-full sm:w-[520px] sm:h-[720px] max-w-[95vw] max-h-[95vh] bg-slate-950 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-gradient-to-r from-purple-900/30 to-slate-900/30">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-purple-300" />
            <div>
              <p className="text-white text-sm font-semibold">
                {MODE_LABEL[mode] || 'Trade'} via Transak
              </p>
              <p className="text-xs text-purple-200/60">
                {config?.environment || '…'} · BSC · {config?.fiat_currency || 'EUR'}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            data-testid="transak-modal-close"
            aria-label="Close"
            className="h-8 w-8 rounded-lg hover:bg-white/10 flex items-center justify-center text-gray-300 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 relative bg-slate-900">
          {loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
              <p className="text-sm text-gray-300">Creating secure Transak session…</p>
            </div>
          )}

          {error && !loading && (
            <div
              className="absolute inset-0 flex items-center justify-center p-6"
              data-testid="transak-modal-error"
            >
              <div className="max-w-sm text-center">
                <AlertTriangle className="h-10 w-10 text-yellow-400 mx-auto mb-3" />
                <p className="text-white font-semibold mb-1">Cannot open Transak</p>
                <p className="text-sm text-gray-300 mb-4">{error}</p>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {widgetUrl && !error && (
            <iframe
              ref={iframeRef}
              src={widgetUrl}
              title="Transak Widget"
              data-testid="transak-widget-iframe"
              allow="camera;microphone;fullscreen;payment;accelerometer;autoplay;geolocation"
              allowFullScreen
              className="w-full h-full border-0"
              onLoad={() => setLoading(false)}
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-white/10 bg-slate-950 flex items-center justify-between text-[11px] text-gray-500">
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3 w-3" />
            Non-custodial · single-use session (5 min)
          </span>
          {lastEvent && (
            <span className="font-mono text-purple-300" data-testid="transak-last-event">
              {lastEvent.name.replace('TRANSAK_', '').toLowerCase()}
            </span>
          )}
          {widgetUrl && !lastEvent && (
            <a
              href={widgetUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 hover:text-purple-300"
            >
              Open in new tab <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransakIframeModal;
