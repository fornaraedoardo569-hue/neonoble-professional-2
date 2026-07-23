import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

export const CryptoSelector = ({ symbols, selected, onSelect }) => (
  <div className="mb-6">
    <label className="block text-sm font-medium text-gray-300 mb-3">Select Cryptocurrency</label>
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
      {symbols.map((crypto) => (
        <button
          key={crypto}
          onClick={() => onSelect(crypto)}
          className={`py-2 px-3 rounded-lg font-medium text-sm transition-all ${
            selected === crypto
              ? 'bg-purple-600 text-white'
              : 'bg-white/5 text-gray-400 hover:bg-white/10'
          }`}
          data-testid={`crypto-${crypto}`}
        >
          {crypto}
        </button>
      ))}
    </div>
    {selected === 'NENO' && (
      <p className="text-xs text-purple-400 mt-2">NENO is fixed at €10,000 per token</p>
    )}
  </div>
);

export const RampTabs = ({ activeTab, onChange }) => (
  <div className="flex space-x-2 mb-6">
    <TabButton
      active={activeTab === 'onramp'}
      onClick={() => onChange('onramp')}
      icon={<ArrowUpRight className="h-5 w-5" />}
      label="Buy Crypto"
      testId="tab-onramp"
    />
    <TabButton
      active={activeTab === 'offramp'}
      onClick={() => onChange('offramp')}
      icon={<ArrowDownRight className="h-5 w-5" />}
      label="Sell Crypto"
      testId="tab-offramp"
    />
  </div>
);

const TabButton = ({ active, onClick, icon, label, testId }) => (
  <button
    onClick={onClick}
    className={`flex-1 py-3 px-4 rounded-xl font-medium flex items-center justify-center space-x-2 transition-all ${
      active ? 'bg-purple-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
    }`}
    data-testid={testId}
  >
    {icon}
    <span>{label}</span>
  </button>
);
