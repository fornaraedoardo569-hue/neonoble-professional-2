import api from './index';

export const transakApi = {
  getConfig: async () => {
    const { data } = await api.get('/transak/config');
    return data;
  },
  logEvent: async (walletAddress, eventType, payload = {}) => {
    const { data } = await api.post('/transak/events', {
      wallet_address: walletAddress,
      event_type: eventType,
      payload,
    });
    return data;
  },
  listEvents: async (walletAddress, limit = 50) => {
    const { data } = await api.get('/transak/events', {
      params: { wallet_address: walletAddress, limit },
    });
    return data;
  },
};
