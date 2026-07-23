import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePricing } from '../hooks/usePricing';
import { useTransactions } from '../hooks/useTransactions';
import { onboardingApi } from '../api';
import { Coins, LogOut, ShieldCheck, ArrowRight } from 'lucide-react';
import { PriceDisplay } from '../components/dashboard/PriceDisplay';
import { TransactionList } from '../components/dashboard/TransactionList';
import { RampPanel } from '../components/dashboard/RampPanel';
import { StartTradingCard } from '../components/dashboard/StartTradingCard';
import { AssistantWidget } from '../components/assistant/AssistantWidget';

const POPULAR_CRYPTOS = ['BTC', 'ETH', 'NENO', 'USDT', 'SOL', 'BNB'];

export default function Dashboard() {
  const { user, logout, isDeveloper } = useAuth();
  const navigate = useNavigate();
  const { prices, loading: loadingPrices, refresh: refreshPrices } = usePricing();
  const { transactions, refresh: refreshTransactions } = useTransactions();
  const [kycStatus, setKycStatus] = useState(null);

  useEffect(() => {
    onboardingApi.myKyc().then((d) => setKycStatus(d?.status || 'NOT_STARTED')).catch(() => {});
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="dashboard">
      <header className="border-b border-white/10 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-2">
              <Coins className="h-8 w-8 text-purple-400" />
              <span className="text-xl font-bold text-white">NeoNoble Ramp</span>
            </Link>
            <div className="flex items-center space-x-4">
              <Link
                to="/transak"
                className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                data-testid="nav-transak-demo"
              >
                Transak Demo
              </Link>
              {isDeveloper && (
                <Link
                  to="/dev"
                  className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                  data-testid="nav-dev-portal"
                >
                  Dev Portal
                </Link>
              )}
              <Link
                to="/change-password"
                className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                data-testid="nav-change-password"
              >
                Change Password
              </Link>
              <span className="text-gray-400 text-sm">{user?.email}</span>
              <button
                onClick={handleLogout}
                className="text-gray-400 hover:text-white p-2"
                data-testid="logout-btn"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {kycStatus && kycStatus !== 'APPROVED' && (
          <Link
            to="/onboarding"
            data-testid="kyc-onboarding-banner"
            className="mb-6 rounded-2xl border border-purple-500/30 bg-purple-500/10 p-4 flex items-center gap-4 hover:bg-purple-500/20 transition-colors"
          >
            <ShieldCheck className="h-8 w-8 text-purple-300 flex-shrink-0" />
            <div className="flex-1 text-sm">
              <p className="font-semibold text-white">
                {kycStatus === 'NOT_STARTED' && 'Complete identity verification to unlock trading'}
                {kycStatus === 'PENDING' && 'Continue your KYC — upload your documents'}
                {kycStatus === 'IN_REVIEW' && 'Your KYC is under review by our compliance team'}
                {kycStatus === 'REJECTED' && 'Your KYC was rejected — view details'}
                {kycStatus === 'ON_HOLD' && 'Your KYC is on hold — additional documents needed'}
              </p>
              <p className="text-purple-200/80 mt-0.5">
                NeoNoble Ramp is a CASP under MiCAR — all customers must complete KYC.
              </p>
            </div>
            <ArrowRight className="h-5 w-5 text-purple-300" />
          </Link>
        )}
        <div className="mb-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4" data-testid="enterprise-otc-banner">
          <div className="flex items-start gap-3">
            <span className="inline-block bg-amber-500/30 text-amber-100 text-xs px-2 py-0.5 rounded font-semibold mt-0.5">
              ENTERPRISE OTC
            </span>
            <div className="flex-1 text-sm text-amber-100/90">
              <p>
                This dashboard is the <strong>direct NeoNoble OTC desk</strong>: NENO at the fixed{' '}
                <span className="font-mono">€10,000</span> price, settled by NeoNoble via Stripe SEPA.
                It's the right channel for bilateral enterprise deals and is operated under
                NeoNoble's own compliance regime.
              </p>
              <p className="mt-2">
                For the retail, non-custodial flow at <em>market price</em> (USDC/USDT/ETH/BTC and,
                once whitelisted, NENO) use the{' '}
                <Link to="/transak" className="text-purple-300 underline hover:text-purple-200">
                  Transak ramp
                </Link>{' '}
                instead — same wallet, different rails.
              </p>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <StartTradingCard
              kycStatus={isDeveloper ? 'APPROVED' : kycStatus}
            />
            <RampPanel onTransactionExecuted={refreshTransactions} />
          </div>
          <div className="space-y-6">
            <PriceDisplay
              symbols={POPULAR_CRYPTOS}
              prices={prices}
              loading={loadingPrices}
              onRefresh={refreshPrices}
            />
            <TransactionList transactions={transactions} />
          </div>
        </div>
      </div>
      <AssistantWidget context="dashboard" />
    </div>
  );
}
