import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowDownUp, Loader2, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  BSC_USDC,
  getTokenInfo,
  getSwapQuote,
  executeSwap,
} from '../../lib/pancakeswap';
import { BrowserProvider } from 'ethers';

const SLIPPAGE_PRESETS = [
  { label: '0.5%', bps: 50 },
  { label: '1%', bps: 100 },
  { label: '3%', bps: 300 },
];

const STEP_LABELS = {
  allowance: 'Checking allowance…',
  approving: 'Awaiting approval signature…',
  approve_sent: 'Approval tx broadcasting…',
  approved: 'Approved. Preparing swap…',
  swapping: 'Awaiting swap signature…',
  swap_sent: 'Swap tx broadcasting…',
  done: 'Swap confirmed on-chain ✓',
};

const useDebounced = (value, delay = 350) => {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
};

export const PancakeSwapPanel = ({ walletAddress, isBSC, nenoContract }) => {
  const [nenoToken, setNenoToken] = useState(null);
  const [direction, setDirection] = useState('BUY_NENO'); // BUY_NENO = USDC->NENO, SELL_NENO = NENO->USDC
  const [amount, setAmount] = useState('');
  const debouncedAmount = useDebounced(amount);
  const [slippageBps, setSlippageBps] = useState(100);

  const [tokenInfoError, setTokenInfoError] = useState('');
  const [quote, setQuote] = useState(null);
  const [quoteError, setQuoteError] = useState('');
  const [quoting, setQuoting] = useState(false);

  const [swapping, setSwapping] = useState(false);
  const [step, setStep] = useState(null);
  const [txHash, setTxHash] = useState('');
  const [swapError, setSwapError] = useState('');

  // Load NENO token info (decimals + symbol) once we have wallet + chain
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!walletAddress || !isBSC || !nenoContract) {
        setNenoToken(null);
        return;
      }
      try {
        const provider = new BrowserProvider(window.ethereum);
        const info = await getTokenInfo(nenoContract, provider);
        if (!cancelled) {
          setNenoToken(info);
          setTokenInfoError('');
        }
      } catch (err) {
        if (!cancelled) {
          setNenoToken(null);
          setTokenInfoError(
            'NENO contract not found on this network. Make sure your wallet is on BSC mainnet and the contract is deployed there.'
          );
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [walletAddress, isBSC, nenoContract]);

  const fromToken = useMemo(() => {
    if (!nenoToken) return null;
    return direction === 'BUY_NENO' ? BSC_USDC : nenoToken;
  }, [direction, nenoToken]);

  const toToken = useMemo(() => {
    if (!nenoToken) return null;
    return direction === 'BUY_NENO' ? nenoToken : BSC_USDC;
  }, [direction, nenoToken]);

  // Re-quote whenever inputs settle
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setQuote(null);
      setQuoteError('');
      if (!fromToken || !toToken) return;
      const numeric = parseFloat(debouncedAmount);
      if (!debouncedAmount || isNaN(numeric) || numeric <= 0) return;
      setQuoting(true);
      try {
        const q = await getSwapQuote({
          amountInHuman: debouncedAmount,
          fromToken,
          toToken,
        });
        if (!cancelled) setQuote(q);
      } catch (err) {
        if (!cancelled) setQuoteError(err.message || 'Failed to fetch quote');
      } finally {
        if (!cancelled) setQuoting(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [debouncedAmount, fromToken, toToken]);

  const handleSwap = useCallback(async () => {
    setSwapError('');
    setTxHash('');
    setStep(null);
    setSwapping(true);
    try {
      const hash = await executeSwap({
        amountInHuman: amount,
        fromToken,
        toToken,
        slippageBps,
        onProgress: (p) => setStep(p.step),
      });
      setTxHash(hash);
    } catch (err) {
      setSwapError(
        err?.shortMessage || err?.reason || err?.message || 'Swap failed'
      );
    } finally {
      setSwapping(false);
    }
  }, [amount, fromToken, toToken, slippageBps]);

  const flipDirection = () =>
    setDirection((d) => (d === 'BUY_NENO' ? 'SELL_NENO' : 'BUY_NENO'));

  const disabled =
    !walletAddress ||
    !isBSC ||
    !nenoToken ||
    !amount ||
    parseFloat(amount) <= 0 ||
    !quote ||
    swapping;

  return (
    <div
      className="rounded-2xl border border-white/10 bg-white/5 p-6"
      data-testid="pancake-swap-panel"
    >
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-white text-lg font-semibold">Step 3 — On-chain Swap (PancakeSwap)</h2>
        <span className="text-xs text-yellow-300 uppercase tracking-wider">BSC mainnet</span>
      </div>
      <p className="text-gray-300 text-sm mb-4">
        Direct USDC ↔ NENO swap through PancakeSwap V2. Price is determined by the AMM pool;
        you sign every transaction yourself. NeoNoble never touches your funds.
      </p>

      {tokenInfoError && (
        <div className="rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-3 text-yellow-200 text-sm mb-4 flex items-start gap-2" data-testid="pancake-token-error">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{tokenInfoError}</span>
        </div>
      )}

      {/* From */}
      <div className="rounded-xl bg-black/20 border border-white/5 p-4 mb-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">From</span>
          <span className="text-xs text-purple-200 font-mono" data-testid="from-token">
            {fromToken?.symbol || '—'}
          </span>
        </div>
        <input
          type="number"
          min="0"
          step="any"
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.0"
          className="w-full bg-transparent text-white text-2xl font-mono focus:outline-none"
          data-testid="swap-amount-input"
          disabled={!fromToken || swapping}
        />
      </div>

      <div className="flex justify-center -my-1 relative z-10">
        <button
          onClick={flipDirection}
          className="bg-slate-800 border border-white/10 rounded-full p-1.5 text-gray-300 hover:text-white hover:bg-slate-700"
          data-testid="flip-direction-btn"
          disabled={swapping}
          title="Flip direction"
        >
          <ArrowDownUp className="h-4 w-4" />
        </button>
      </div>

      {/* To (quote) */}
      <div className="rounded-xl bg-black/20 border border-white/5 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">You receive (estimate)</span>
          <span className="text-xs text-purple-200 font-mono" data-testid="to-token">
            {toToken?.symbol || '—'}
          </span>
        </div>
        <div className="text-white text-2xl font-mono min-h-[2.25rem]" data-testid="swap-quote-out">
          {quoting ? (
            <Loader2 className="h-5 w-5 animate-spin text-purple-300" />
          ) : quote ? (
            Number(quote.amountOutHuman).toFixed(6)
          ) : (
            '—'
          )}
        </div>
        {quote && (
          <p className="text-xs text-gray-500 mt-1">
            Rate: 1 {fromToken.symbol} ≈{' '}
            <span className="font-mono">
              {(Number(quote.amountOutHuman) / parseFloat(amount)).toFixed(6)}
            </span>{' '}
            {toToken.symbol}
          </p>
        )}
        {quoteError && (
          <p
            className="text-xs text-red-300 mt-2 flex items-start gap-1"
            data-testid="quote-error"
          >
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
            <span>{quoteError}</span>
          </p>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2">
        <span className="text-xs text-gray-400">Slippage:</span>
        {SLIPPAGE_PRESETS.map((p) => (
          <button
            key={p.bps}
            onClick={() => setSlippageBps(p.bps)}
            className={`text-xs px-2 py-1 rounded ${
              slippageBps === p.bps
                ? 'bg-purple-600 text-white'
                : 'bg-white/5 text-gray-300 hover:bg-white/10'
            }`}
            data-testid={`slippage-${p.bps}`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <button
        onClick={handleSwap}
        disabled={disabled}
        className="w-full mt-5 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/40 text-white py-3 rounded-xl font-semibold flex items-center justify-center gap-2"
        data-testid="pancake-swap-btn"
      >
        {swapping ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{STEP_LABELS[step] || 'Working…'}</span>
          </>
        ) : (
          <span>
            Swap {fromToken?.symbol || ''} → {toToken?.symbol || ''}
          </span>
        )}
      </button>

      {!walletAddress && (
        <p className="text-yellow-300 text-xs mt-3" data-testid="pancake-disabled-note">
          Connect your wallet first.
        </p>
      )}
      {walletAddress && !isBSC && (
        <p className="text-yellow-300 text-xs mt-3">
          Switch your wallet to BNB Smart Chain to swap.
        </p>
      )}

      {swapError && (
        <div
          className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-red-200 text-sm flex items-start gap-2"
          data-testid="swap-error"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{swapError}</span>
        </div>
      )}

      {txHash && (
        <div
          className="mt-4 rounded-lg border border-green-500/40 bg-green-500/10 p-3 text-green-100 text-sm flex items-start gap-2"
          data-testid="swap-success"
        >
          <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0 text-green-300" />
          <div className="min-w-0 flex-1">
            <p>Swap confirmed on-chain.</p>
            <a
              href={`https://bscscan.com/tx/${txHash}`}
              target="_blank"
              rel="noreferrer"
              className="text-green-300 underline text-xs font-mono inline-flex items-center gap-1 mt-1 break-all"
            >
              <ExternalLink className="h-3 w-3 flex-shrink-0" />
              {txHash}
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
