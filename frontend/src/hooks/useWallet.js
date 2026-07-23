import { useCallback, useEffect, useState } from 'react';

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

const BSC_HEX_CHAIN_ID = '0x38'; // BSC mainnet
const BSC_NETWORK_PARAMS = {
  chainId: BSC_HEX_CHAIN_ID,
  chainName: 'BNB Smart Chain',
  nativeCurrency: { name: 'BNB', symbol: 'BNB', decimals: 18 },
  rpcUrls: ['https://bsc-dataseed.binance.org/'],
  blockExplorerUrls: ['https://bscscan.com'],
};

/**
 * Non-custodial wallet connection via injected provider (MetaMask, etc.).
 *
 * The user explicitly approves connection in their wallet — there is no
 * backend storage of private keys and the platform never has signing
 * authority. The returned address is the *only* destination Transak will
 * deliver crypto to.
 */
export function useWallet() {
  const [address, setAddress] = useState(null);
  const [chainId, setChainId] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');

  const provider = typeof window !== 'undefined' ? window.ethereum : null;
  const hasInjectedWallet = !!provider;

  const refreshChain = useCallback(async () => {
    if (!provider) return;
    try {
      const id = await provider.request({ method: 'eth_chainId' });
      setChainId(id);
    } catch (err) {
      devError('Failed to read chainId:', err);
    }
  }, [provider]);

  const connect = useCallback(async () => {
    setError('');
    if (!provider) {
      setError('No browser wallet detected. Install MetaMask to continue.');
      return null;
    }
    setConnecting(true);
    try {
      const accounts = await provider.request({ method: 'eth_requestAccounts' });
      const next = accounts?.[0] || null;
      setAddress(next);
      await refreshChain();
      return next;
    } catch (err) {
      const message = err?.message || 'Wallet connection rejected';
      setError(message);
      return null;
    } finally {
      setConnecting(false);
    }
  }, [provider, refreshChain]);

  const switchToBSC = useCallback(async () => {
    if (!provider) return false;
    try {
      await provider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: BSC_HEX_CHAIN_ID }],
      });
      await refreshChain();
      return true;
    } catch (err) {
      // 4902 = chain not added yet
      if (err?.code === 4902) {
        try {
          await provider.request({
            method: 'wallet_addEthereumChain',
            params: [BSC_NETWORK_PARAMS],
          });
          await refreshChain();
          return true;
        } catch (innerErr) {
          devError('Failed to add BSC network:', innerErr);
          setError('Could not add BSC network to your wallet');
          return false;
        }
      }
      devError('Failed to switch to BSC:', err);
      setError('Could not switch to BSC network');
      return false;
    }
  }, [provider, refreshChain]);

  const disconnect = useCallback(() => {
    setAddress(null);
    setChainId(null);
    setError('');
  }, []);

  useEffect(() => {
    if (!provider) return undefined;
    const onAccountsChanged = (accounts) => {
      setAddress(accounts?.[0] || null);
    };
    const onChainChanged = (id) => setChainId(id);
    provider.on?.('accountsChanged', onAccountsChanged);
    provider.on?.('chainChanged', onChainChanged);
    return () => {
      provider.removeListener?.('accountsChanged', onAccountsChanged);
      provider.removeListener?.('chainChanged', onChainChanged);
    };
  }, [provider]);

  return {
    address,
    chainId,
    isBSC: chainId === BSC_HEX_CHAIN_ID,
    hasInjectedWallet,
    connecting,
    error,
    connect,
    switchToBSC,
    disconnect,
  };
}
