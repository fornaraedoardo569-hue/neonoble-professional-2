import React from 'react';
import { History } from 'lucide-react';

const STATUS_STYLES = {
  COMPLETED: 'bg-green-500/20 text-green-400',
  PROCESSING: 'bg-yellow-500/20 text-yellow-400',
};

export const TransactionList = ({ transactions, limit = 5 }) => (
  <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6" data-testid="transaction-list">
    <h3 className="text-lg font-semibold text-white flex items-center mb-4">
      <History className="h-5 w-5 mr-2 text-purple-400" /> Recent Transactions
    </h3>
    {transactions.length === 0 ? (
      <p className="text-gray-400 text-sm">No transactions yet</p>
    ) : (
      <div className="space-y-3">
        {transactions.slice(0, limit).map((tx) => (
          <div
            key={tx.id}
            className="flex justify-between items-center py-2 border-b border-white/5 last:border-0"
            data-testid={`transaction-${tx.id}`}
          >
            <div>
              <p className="text-white text-sm font-medium">
                {tx.type === 'ONRAMP' ? 'Bought' : 'Sold'} {tx.crypto_amount} {tx.crypto_currency}
              </p>
              <p className="text-gray-500 text-xs">{tx.reference}</p>
            </div>
            <span
              className={`text-xs px-2 py-1 rounded ${
                STATUS_STYLES[tx.status] || 'bg-gray-500/20 text-gray-400'
              }`}
            >
              {tx.status}
            </span>
          </div>
        ))}
      </div>
    )}
  </div>
);
