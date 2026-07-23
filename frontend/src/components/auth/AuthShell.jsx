import React from 'react';
import { Link } from 'react-router-dom';
import { Coins } from 'lucide-react';

export const AuthShell = ({ title, subtitle, children, footer }) => (
  <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center px-4">
    <div className="max-w-md w-full">
      <div className="text-center mb-8">
        <Link to="/" className="inline-flex items-center space-x-2">
          <Coins className="h-10 w-10 text-purple-400" />
          <span className="text-2xl font-bold text-white">NeoNoble Ramp</span>
        </Link>
        <h1 className="mt-6 text-3xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-gray-400 mt-2">{subtitle}</p>}
      </div>
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
        {children}
        {footer && <div className="mt-6 text-center">{footer}</div>}
      </div>
    </div>
  </div>
);
