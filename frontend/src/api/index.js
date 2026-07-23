import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

// Token storage keys
const ACCESS_TOKEN_KEY = 'token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (access, refresh) => {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Silent refresh: on 401, try refreshing once, then retry the original request.
let refreshInFlight = null;

async function performRefresh() {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
      refresh_token: refresh,
    });
    if (data?.access_token) {
      tokenStore.setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    }
  } catch (err) {
    if (process.env.NODE_ENV === 'development') {
      // eslint-disable-next-line no-console
      console.error('Token refresh failed:', err);
    }
  }
  tokenStore.clear();
  return null;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    if (status === 401 && original && !original._retry && tokenStore.getRefresh()) {
      original._retry = true;
      if (!refreshInFlight) {
        refreshInFlight = performRefresh().finally(() => {
          refreshInFlight = null;
        });
      }
      const newToken = await refreshInFlight;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    // KYC required (403 with structured detail) — emit a global event so any
    // page can route the user to /onboarding without duplicating logic.
    if (status === 403) {
      const detail = error.response?.data?.detail;
      if (detail && typeof detail === 'object' && detail.error === 'kyc_required') {
        try {
          window.dispatchEvent(
            new CustomEvent('neonoble:kyc-required', { detail })
          );
        } catch (_) {}
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: async (email, password, role = 'USER') => {
    const response = await api.post('/auth/register', { email, password, role });
    return response.data;
  },
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
};

// Ramp API (for users)
export const rampApi = {
  getPrices: async () => {
    const response = await api.get('/ramp/prices');
    return response.data;
  },
  createOnrampQuote: async (fiatAmount, cryptoCurrency) => {
    const response = await api.post('/ramp/onramp/quote', {
      fiat_amount: fiatAmount,
      crypto_currency: cryptoCurrency,
    });
    return response.data;
  },
  executeOnramp: async (quoteId, walletAddress) => {
    const response = await api.post('/ramp/onramp/execute', {
      quote_id: quoteId,
      wallet_address: walletAddress,
    });
    return response.data;
  },
  createOfframpQuote: async (cryptoAmount, cryptoCurrency) => {
    const response = await api.post('/ramp/offramp/quote', {
      crypto_amount: cryptoAmount,
      crypto_currency: cryptoCurrency,
    });
    return response.data;
  },
  executeOfframp: async (quoteId, bankAccount) => {
    const response = await api.post('/ramp/offramp/execute', {
      quote_id: quoteId,
      bank_account: bankAccount,
    });
    return response.data;
  },
  getTransactions: async () => {
    const response = await api.get('/ramp/transactions');
    return response.data;
  },
};

// Developer API
export const devApi = {
  getApiKeys: async () => {
    const response = await api.get('/dev/api-keys');
    return response.data;
  },
  createApiKey: async (name, description = '', rateLimit = 1000) => {
    const response = await api.post('/dev/api-keys', {
      name,
      description,
      rate_limit: rateLimit,
    });
    return response.data;
  },
  revokeApiKey: async (keyId) => {
    const response = await api.delete(`/dev/api-keys/${keyId}`);
    return response.data;
  },
  getDashboard: async () => {
    const response = await api.get('/dev/dashboard');
    return response.data;
  },
};

// Health check
export const healthApi = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
  rampHealth: async () => {
    const response = await api.get('/ramp-api-health');
    return response.data;
  },
};

// CASP Admin Console API
export const caspApi = {
  // Dashboard
  dashboard: async () => (await api.get('/casp/dashboard')).data,
  // Block 1
  listKyc: async (status) => (await api.get('/casp/kyc', { params: { status } })).data,
  decideKyc: async (kycId, decision, reason) =>
    (await api.post(`/casp/kyc/${kycId}/decision`, { decision, reason })).data,
  listKyb: async () => (await api.get('/casp/kyb')).data,
  listRisk: async () => (await api.get('/casp/risk-rating')).data,
  upsertRisk: async (body) => (await api.post('/casp/risk-rating', body)).data,
  listSanctions: async () => (await api.get('/casp/sanctions')).data,
  // Block 2
  listAml: async (status, severity) =>
    (await api.get('/casp/aml/alerts', { params: { status, severity } })).data,
  screenAddress: async (body) => (await api.post('/casp/aml/screen-address', body)).data,
  resolveAml: async (id, status, notes) =>
    (await api.post(`/casp/aml/alerts/${id}/resolve`, { status, notes })).data,
  listTravelRule: async (direction) =>
    (await api.get('/casp/travel-rule', { params: { direction } })).data,
  createTravelRule: async (body) => (await api.post('/casp/travel-rule', body)).data,
  listSar: async () => (await api.get('/casp/sar')).data,
  draftSar: async (body) => (await api.post('/casp/sar', body)).data,
  // Block 3
  listWallets: async (kind, purpose) =>
    (await api.get('/casp/wallets', { params: { kind, purpose } })).data,
  provisionWallet: async (body) => (await api.post('/casp/wallets/provision', body)).data,
  freezeWallet: async (id) => (await api.post(`/casp/wallets/${id}/freeze`)).data,
  reconcileWallet: async (id) => (await api.post(`/casp/wallets/${id}/reconcile`)).data,
  latestPor: async () => (await api.get('/casp/proof-of-reserves')).data,
  generatePor: async () => (await api.post('/casp/proof-of-reserves/generate')).data,
  // Block 4
  listOtc: async (status) => (await api.get('/casp/otc', { params: { status } })).data,
  createOtc: async (body) => (await api.post('/casp/otc/quote', body)).data,
  approveOtc: async (id, decision, notes) =>
    (await api.post(`/casp/otc/${id}/approve`, { decision, notes })).data,
  executeOtc: async (id) => (await api.post(`/casp/otc/${id}/execute`)).data,
  // Block 5
  listReports: async () => (await api.get('/casp/reports')).data,
  generateMicar: async (body) => (await api.post('/casp/reports/micar', body)).data,
  upsertCapital: async (body) => (await api.post('/casp/capital', body)).data,
  // Autonomy
  sanctionsStatus: async () => (await api.get('/casp/sanctions/status')).data,
  sanctionsRefresh: async () => (await api.post('/casp/sanctions/refresh')).data,
  listVasps: async () => (await api.get('/casp/trp/vasps')).data,
  upsertVasp: async (body) => (await api.post('/casp/trp/vasps', body)).data,
  listTrpInbox: async () => (await api.get('/casp/trp/inbox')).data,
  decideTrpInbox: async (id, decision, notes) =>
    (await api.post(`/casp/trp/inbox/${id}/decision`, { decision, notes })).data,
  deleteVasp: async (did) => (await api.delete(`/casp/trp/vasps/${encodeURIComponent(did)}`)).data,
  uploadKycDocument: async (kycId, body) => (await api.post(`/casp/kyc/${kycId}/documents`, body)).data,
  listKycDocuments: async (kycId) => (await api.get(`/casp/kyc/${kycId}/documents`)).data,
  // Setup wizard (live mode)
  setupStatus: async () => (await api.get('/casp/setup/status')).data,
  setupLegalEntity: async (body) => (await api.post('/casp/setup/legal-entity', body)).data,
  setupMarkWiped: async () => (await api.post('/casp/setup/mark-demo-wiped')).data,
  // Block 6
  listComplaints: async (status) =>
    (await api.get('/casp/complaints', { params: { status } })).data,
  createComplaint: async (body) => (await api.post('/casp/complaints', body)).data,
  listDisclosures: async () => (await api.get('/casp/disclosures')).data,
  // Block 7
  listAdmins: async () => (await api.get('/casp/governance/admins')).data,
  addAdmin: async (body) => (await api.post('/casp/governance/admins', body)).data,
  listIncidents: async (status) =>
    (await api.get('/casp/governance/incidents', { params: { status } })).data,
  listConflicts: async () => (await api.get('/casp/governance/conflicts')).data,
  // Audit
  listAudit: async (limit = 100, entityId) =>
    (await api.get('/casp/audit', { params: { limit, entity_id: entityId } })).data,
  verifyAudit: async () => (await api.get('/casp/audit/verify')).data,
};

// Customer Onboarding (KYC self-service)
export const onboardingApi = {
  myKyc: async () => (await api.get('/onboarding/my-kyc')).data,
  startKyc: async (body) => (await api.post('/onboarding/kyc/start', body)).data,
  uploadDocument: async (body) => (await api.post('/onboarding/kyc/document', body)).data,
};

export default api;
