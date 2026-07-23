"""Internal/autonomous CASP provider implementations.

Drop-in replacements for the external vendor adapters (Sumsub, Chainalysis,
Fireblocks, Notabene). Selected automatically by the CaspService factory
when CASP_AUTONOMOUS_MODE=true (default).

Design goals:
  * 100% in-house, no recurring SaaS fees.
  * Same interfaces as the external adapters (services/casp/base.py) so
    consumer code (routes, services) does not need to change.
  * Backed only by free public data sources: OFAC SDN list, EU consolidated
    sanctions, Etherscan/BscScan public APIs (free tier), open IVMS-101 spec.
"""
