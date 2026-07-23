import React from 'react';

export const QuoteCard = ({ activeTab, quote }) => (
  <div className="bg-white/5 rounded-xl p-4 mb-6" data-testid="quote-display">
    <div className="flex justify-between items-center mb-4">
      <span className="text-gray-400">Quote</span>
      <span className="text-xs text-gray-500">
        Expires: {new Date(quote.valid_until).toLocaleTimeString()}
      </span>
    </div>
    <div className="space-y-3">
      <Row
        label={`You ${activeTab === 'onramp' ? 'Pay' : 'Sell'}`}
        value={
          activeTab === 'onramp'
            ? `€${quote.fiat_amount}`
            : `${quote.crypto_amount} ${quote.crypto_currency}`
        }
      />
      <Row
        label="Exchange Rate"
        value={`1 ${quote.crypto_currency} = €${quote.exchange_rate.toLocaleString()}`}
      />
      <Row label={`Fee (${quote.fee_percentage}%)`} value={`€${quote.fee_amount}`} />
      <div className="border-t border-white/10 pt-3 flex justify-between">
        <span className="text-gray-300 font-medium">
          You {activeTab === 'onramp' ? 'Receive' : 'Get'}
        </span>
        <span className="text-white text-lg font-bold">
          {activeTab === 'onramp'
            ? `${quote.crypto_amount} ${quote.crypto_currency}`
            : `€${quote.total_fiat}`}
        </span>
      </div>
      <p className="text-xs text-gray-500">Price source: {quote.price_source}</p>
    </div>
  </div>
);

const Row = ({ label, value }) => (
  <div className="flex justify-between">
    <span className="text-gray-400">{label}</span>
    <span className="text-white font-medium">{value}</span>
  </div>
);
