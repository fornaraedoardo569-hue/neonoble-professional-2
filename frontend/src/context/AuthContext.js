import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, tokenStore } from '../api';

const AuthContext = createContext(null);

const devError = (...args) => {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    if (!tokenStore.getAccess() && !tokenStore.getRefresh()) {
      setLoading(false);
      return;
    }

    try {
      const userData = await authApi.getMe();
      setUser(userData);
    } catch (err) {
      devError('Auth check failed:', err);
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const persistAuth = useCallback((response) => {
    const access = response.access_token || response.token;
    const refresh = response.refresh_token;
    if (access) {
      tokenStore.setTokens(access, refresh);
      setUser(response.user);
      return true;
    }
    return false;
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const response = await authApi.login(email, password);
      if (response.success && persistAuth(response)) {
        return { success: true };
      }
      throw new Error(response.message || 'Login failed');
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Login failed';
      setError(message);
      return { success: false, error: message };
    }
  }, [persistAuth]);

  const register = useCallback(async (email, password, role = 'USER') => {
    setError(null);
    try {
      const response = await authApi.register(email, password, role);
      if (response.success && persistAuth(response)) {
        return { success: true };
      }
      throw new Error(response.message || 'Registration failed');
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Registration failed';
      setError(message);
      return { success: false, error: message };
    }
  }, [persistAuth]);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isDeveloper: user?.role === 'DEVELOPER' || user?.role === 'ADMIN',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
