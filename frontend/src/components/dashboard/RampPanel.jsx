import React, { useState } from 'react';
import { Wallet, Building, RefreshCw, Loader2 } from 'lucide-react';
import { rampApi } from '../../api';
import { AlertBanner } from './AlertBanner';
import { CryptoSelector, RampTabs } from './RampControls';
import { QuoteCard } from './QuoteCard';

const POPULAR_CRYPTOS = ['BTC', 'ETH', 'NENO', 'USDT', 'SOL', 'BNB'];

export const RampPanel = ({ onTransactionExecuted }) => {
  const [activeTab, setActiveTab] = useState('onramp');
  const [selectedCrypto, setSelectedCrypto] = useState('BTC');
  const [fiatAmount, setFiatAmount] = useState('');
  const [cryptoAmount, setCryptoAmount] = useState('');
  const [walletAddress, setWalletAddress] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const resetQuote = () => setQuote(null);

  const switchTab = (tab) => {
    setActiveTab(tab);
    resetQuote();
    setError('');
  };

  const handleCryptoSelect = (crypto) => {
    setSelectedCrypto(crypto);
    resetQuote();
  };

  const getQuote = async () => {
    setError('');
    setQuote(null);
    setLoadingQuote(true);
    try {
      if (activeTab === 'onramp') {
        if (!fiatAmount || parseFloat(fiatAmount) <= 0) {
          throw new Error('Please enter a valid EUR amount');
        }
        const data = await rampApi.createOnrampQuote(parseFloat(fiatAmount), selectedCrypto);
        setQuote(data);
      } else {
        if (!cryptoAmount || parseFloat(cryptoAmount) <= 0) {
          throw new Error('Please enter a valid crypto amount');
        }
        const data = await rampApi.createOfframpQuote(parseFloat(cryptoAmount), selectedCrypto);
        setQuote(data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to get quote');
    } finally {
      setLoadingQuote(false);
    }
  };

  const executeTransaction = async () => {
    setError('');
    setSuccess('');
    setExecuting(true);
    try {
      if (activeTab === 'onramp') {
        if (!walletAddress) throw new Error('Please enter your wallet address');
        await rampApi.executeOnramp(quote.quote_id, walletAddress);
        setSuccess(`Successfully initiated purchase of ${quote.crypto_amount} ${quote.crypto_currency}!`);
      } else {
        if (!bankAccount) throw new Error('Please enter your bank account IBAN');
        await rampApi.executeOfframp(quote.quote_id, bankAccount);
        setSuccess(`Successfully initiated sale of ${quote.crypto_amount} ${quote.crypto_currency}!`);
      }
      setQuote(null);
      setFiatAmount('');
      setCryptoAmount('');
      setWalletAddress('');
      setBankAccount('');
      onTransactionExecuted?.();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Transaction failed');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6">
      <RampTabs activeTab={activeTab} onChange={switchTab} />
      <AlertBanner kind="error" message={error} testId="ramp-error" />
      <AlertBanner kind="success" message={success} testId="ramp-success" />
      <CryptoSelector
        symbols={POPULAR_CRYPTOS}
        selected={selectedCrypto}
        onSelect={handleCryptoSelect}
      />

      <AmountInput
        activeTab={activeTab}
        selectedCrypto={selectedCrypto}
        fiatAmount={fiatAmount}
        cryptoAmount={cryptoAmount}
        onFiatChange={(v) => { setFiatAmount(v); resetQuote(); }}
        onCryptoChange={(v) => { setCryptoAmount(v); resetQuote(); }}
      />

      {!quote && (
        <button
          onClick={getQuote}
          disabled={loadingQuote}
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white py-4 rounded-xl font-semibold flex items-center justify-center space-x-2"
          data-testid="get-quote-btn"
        >
          {loadingQuote ? (
            <><Loader2 className="h-5 w-5 animate-spin" /><span>Getting Quote...</span></>
          ) : (
            <><RefreshCw className="h-5 w-5" /><span>Get Quote</span></>
          )}
        </button>
      )}

      {quote && (
        <>
          <QuoteCard activeTab={activeTab} quote={quote} />
          <DestinationInput
            activeTab={activeTab}
            walletAddress={walletAddress}
            bankAccount={bankAccount}
            onWalletChange={setWalletAddress}
            onBankChange={setBankAccount}
          />
          <button
            onClick={executeTransaction}
            disabled={executing}
            className="w-full mt-4 bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 text-white py-4 rounded-xl font-semibold flex items-center justify-center space-x-2"
            data-testid="execute-btn"
          >
            {executing ? (
              <><Loader2 className="h-5 w-5 animate-spin" /><span>Processing...</span></>
            ) : (
              <span>Confirm {activeTab === 'onramp' ? 'Purchase' : 'Sale'}</span>
            )}
          </button>
          <button
            onClick={resetQuote}
            className="w-full text-gray-400 hover:text-white py-2 mt-2"
            data-testid="cancel-quote-btn"
          >
            Cancel
          </button>
        </>
      )}
    </div>
  );
};

const AmountInput = ({
  activeTab, selectedCrypto, fiatAmount, cryptoAmount, onFiatChange, onCryptoChange,
}) => (
  <div className="mb-6">
    {activeTab === 'onramp' ? (
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">You Pay (EUR)</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">€</span>
          <input
            type="number"
            value={fiatAmount}
            onChange={(e) => onFiatChange(e.target.value)}
            className="w-full pl-10 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white text-xl placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="100.00"
            min="1"
            data-testid="input-fiat-amount"
          />
        </div>
      </div>
    ) : (
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">You Sell ({selectedCrypto})</label>
        <input
          type="number"
          value={cryptoAmount}
          onChange={(e) => onCryptoChange(e.target.value)}
          className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white text-xl placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          placeholder="0.001"
          min="0"
          step="any"
          data-testid="input-crypto-amount"
        />
      </div>
    )}
  </div>
);

const DestinationInput = ({
  activeTab, walletAddress, bankAccount, onWalletChange, onBankChange,
}) =>
  activeTab === 'onramp' ? (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        <Wallet className="h-4 w-4 inline mr-1" /> Wallet Address
      </label>
      <input
        type="text"
        value={walletAddress}
        onChange={(e) => onWalletChange(e.target.value)}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
        placeholder="0x... or bc1..."
        data-testid="input-wallet"
      />
    </div>
  ) : (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        <Building className="h-4 w-4 inline mr-1" /> Bank Account (IBAN)
      </label>
      <input
        type="text"
        value={bankAccount}
        onChange={(e) => onBankChange(e.target.value)}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
        placeholder="DE89 3704 0044 0532 0130 00"
        data-testid="input-bank"
      />
    </div>
  );
