import React from 'react';
import TransakRamp from '../components/TransakRamp';

export default function Ramp() {
  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-5xl font-bold text-center mb-4">NeoNoble Ramp</h1>
        <p className="text-center text-xl text-gray-400 mb-12">On-Ramp e Off-Ramp istantanei</p>

        <div className="grid lg:grid-cols-2 gap-10">
          {/* ON-RAMP */}
          <div className="bg-zinc-900 rounded-3xl p-8 border border-green-500/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">↑</div>
              <h2 className="text-3xl font-semibold">Acquista (On-Ramp)</h2>
            </div>
            <TransakRamp 
              isOnRamp={true} 
              defaultAmount={150} 
            />
          </div>

          {/* OFF-RAMP */}
          <div className="bg-zinc-900 rounded-3xl p-8 border border-orange-500/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">↓</div>
              <h2 className="text-3xl font-semibold">Vendi (Off-Ramp)</h2>
            </div>
            <TransakRamp 
              isOnRamp={false} 
              defaultAmount={80} 
            />
          </div>
        </div>
      </div>
    </div>
  );
}
