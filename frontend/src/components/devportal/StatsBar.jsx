import React from 'react';
import { Key, Shield, Activity } from 'lucide-react';

export const StatsBar = ({ stats }) => {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" data-testid="dev-stats">
      <StatCard icon={<Key className="h-6 w-6 text-purple-400" />} bg="bg-purple-500/20" label="Total API Keys" value={stats.totalKeys} testId="stat-total-keys" />
      <StatCard icon={<Shield className="h-6 w-6 text-green-400" />} bg="bg-green-500/20" label="Active Keys" value={stats.activeKeys} testId="stat-active-keys" />
      <StatCard
        icon={<Activity className="h-6 w-6 text-blue-400" />}
        bg="bg-blue-500/20"
        label="Total API Calls"
        value={stats.totalApiCalls.toLocaleString()}
        testId="stat-total-calls"
      />
    </div>
  );
};

const StatCard = ({ icon, bg, label, value, testId }) => (
  <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6" data-testid={testId}>
    <div className="flex items-center space-x-3">
      <div className={`${bg} p-3 rounded-lg`}>{icon}</div>
      <div>
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
  </div>
);
