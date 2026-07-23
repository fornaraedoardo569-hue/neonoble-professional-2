import React from 'react';
import TransakRamp from '../components/TransakRamp';

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-10">Dashboard NeoNoble</h1>

        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h2 className="text-2xl mb-6 font-semibold">Quick Buy</h2>
            <div className="bg-zinc-900 rounded-3xl p-8">
              <TransakRamp isOnRamp={true} defaultAmount={50} />
            </div>
          </div>

          <div>
            <h2 className="text-2xl mb-6 font-semibold">Quick Sell</h2>
            <div className="bg-zinc-900 rounded-3xl p-8">
              <TransakRamp isOnRamp={false} defaultAmount={30} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
