import { useState, useEffect, useCallback } from 'react';
import { rampApi } from '../api';

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

export function useTransactions() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await rampApi.getTransactions();
      setTransactions(data || []);
    } catch (err) {
      devError('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { transactions, loading, refresh };
}
