import { useState, useEffect, useCallback } from 'react';
import { devApi } from '../api';

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

export function useApiKeys() {
  const [apiKeys, setApiKeys] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const dashboard = await devApi.getDashboard();
      setApiKeys(dashboard.keys || []);
      setStats({
        totalKeys: dashboard.total_keys,
        activeKeys: dashboard.active_keys,
        totalApiCalls: dashboard.total_api_calls,
      });
    } catch (err) {
      devError('Failed to load dashboard:', err);
      setError('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { apiKeys, stats, loading, error, setError, refresh };
}
