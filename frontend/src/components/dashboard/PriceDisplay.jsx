import React from 'react';
import { RefreshCw, TrendingUp } from 'lucide-react';

const formatPrice = (price) => {
  if (price >= 1000) return `€${price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  if (price >= 1) return `€${price.toFixed(2)}`;
  return `€${price.toFixed(4)}`;
};

export const PriceDisplay = ({ symbols, prices, loading, onRefresh }) => (
  <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6" data-testid="price-display">
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-lg font-semibold text-white flex items-center">
        <TrendingUp className="h-5 w-5 mr-2 text-purple-400" /> Live Prices
      </h3>
      <button
        onClick={onRefresh}
        className="text-gray-400 hover:text-white"
        data-testid="refresh-prices-btn"
      >
        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      </button>
    </div>
    <div className="space-y-3">
      {symbols.map((crypto) => (
        <div key={crypto} className="flex justify-between items-center">
          <span className="text-gray-300">{crypto}</span>
          <span className="text-white font-medium" data-testid={`price-${crypto}`}>
            {prices[crypto] ? formatPrice(prices[crypto]) : '...'}
          </span>
        </div>
      ))}
    </div>
  </div>
);
