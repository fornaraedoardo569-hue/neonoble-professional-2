import React from 'react';
import { ShieldCheck, UserCheck, ExternalLink } from 'lucide-react';

const PILLARS = [
  {
    icon: UserCheck,
    title: 'User-initiated Only',
    body:
      'Every Buy or Sell flow requires you to first connect your own wallet on this page and then explicitly sign the trade inside Transak. NeoNoble does not auto-route trades from the backend.',
    testId: 'pillar-user-initiated',
  },
  {
    icon: ShieldCheck,
    title: 'No Fund Intermediation',
    body:
      'Fiat and crypto move directly between you and Transak. NeoNoble does not custody balances, never receives a transient deposit, and never settles trades on your behalf.',
    testId: 'pillar-no-intermediation',
  },
  {
    icon: ExternalLink,
    title: 'Direct Delivery',
    body:
      'The walletAddress passed to Transak is the address you connected above — locked via disableWalletAddressForm so it cannot be edited mid-flow. Crypto lands directly in that wallet.',
    testId: 'pillar-direct-delivery',
  },
];

export const ComplianceBanner = () => (
  <div
    className="rounded-2xl border border-white/10 bg-gradient-to-br from-purple-900/30 to-slate-900/40 p-6"
    data-testid="compliance-banner"
  >
    <div className="flex items-center gap-2 mb-4">
      <ShieldCheck className="h-5 w-5 text-purple-300" />
      <h2 className="text-white font-semibold tracking-tight">Non-custodial by design</h2>
      <span className="text-xs bg-purple-500/20 text-purple-200 px-2 py-0.5 rounded ml-2">
        STAGING
      </span>
    </div>
    <p className="text-gray-300 text-sm mb-5">
      Transak handles the regulated fiat rails and KYC. NeoNoble is the application layer — these
      three pillars are visibly enforced in this page for the UK compliance walkthrough.
    </p>
    <div className="grid md:grid-cols-3 gap-4">
      {PILLARS.map(({ icon: Icon, title, body, testId }) => (
        <div
          key={title}
          className="rounded-xl bg-white/5 p-4 border border-white/5"
          data-testid={testId}
        >
          <div className="flex items-center gap-2 mb-2">
            <Icon className="h-4 w-4 text-purple-300" />
            <h3 className="text-white text-sm font-semibold">{title}</h3>
          </div>
          <p className="text-gray-300 text-xs leading-relaxed">{body}</p>
        </div>
      ))}
    </div>
  </div>
);
