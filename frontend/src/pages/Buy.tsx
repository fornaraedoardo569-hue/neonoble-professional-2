import React from 'react';
import TransakRamp from '../components/TransakRamp';

export default function Buy() {
  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-10">
          <h1 className="text-5xl font-bold mb-3">Acquista Crypto</h1>
          <p className="text-xl text-gray-400">Compra BNB, NENO e altre crypto con carta, bonifico o Apple Pay</p>
        </div>

        <div className="bg-zinc-900/50 border border-gray-800 rounded-3xl p-10">
          <TransakRamp 
            isOnRamp={true} 
            defaultAmount={100} 
          />
        </div>

        <p className="text-center text-sm text-gray-500 mt-8">
          Pagamenti sicuri • KYC semplificato • Powered by Transak
        </p>
      </div>
    </div>
  );
}
