import { useState, useEffect, useCallback } from 'react';
import { rampApi } from '../api';

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

export function usePricing() {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await rampApi.getPrices();
      setPrices(data.prices || {});
    } catch (err) {
      devError('Failed to load prices:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { prices, loading, refresh };
}
