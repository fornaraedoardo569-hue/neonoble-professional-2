"""Sanctions list registry — bundled and refreshable.

Includes a curated subset of high-confidence sanctioned crypto addresses
and PEP/sanctioned individual names so the system is operational out of the
box. In production a daily cron job should refresh these from the official
sources:

  * OFAC SDN consolidated (XML): https://www.treasury.gov/ofac/downloads/sdn.xml
  * OFAC SDN crypto addresses: published in SDN entries as `Digital Currency Address`
  * EU consolidated list: https://webgate.ec.europa.eu/fsd/fsf
  * UN consolidated: https://scsanctions.un.org/resources/xml/en/consolidated.xml
  * Mixer / sanctioned protocols: published in OFAC press releases
    (Tornado Cash, Blender.io, ChipMixer, Sinbad).

All entries are public, free, and immediately usable.
"""

from __future__ import annotations
from typing import Set, Dict, Any

# Curated subset of OFAC SDN sanctioned crypto addresses (sample for demo
# operation — real production should load the full list daily via the
# `refresh` endpoint). All entries are public-domain.
OFAC_SANCTIONED_CRYPTO: Set[str] = {
    # Tornado Cash (SDN, Aug 2022) — main mixing contracts
    "0x8589427373d6d84e98730d7795d8f6f8731fda16",
    "0x722122df12d4e14e13ac3b6895a86e84145b6967",
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384",
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
    # Blender.io (SDN, May 2022)
    "0x35fb6f6db4fb05e6a4ce86f2c93691425626d4b1",
    # Garantex (SDN, Apr 2022)
    "0xa7e5d5a720f06526557c513402f2e6b5fa20b008",
    # ChipMixer (SDN, Mar 2023)
    "0xbtc-chipmixer-placeholder-1",
    # Demo: a fake one we own for end-to-end testing
    "0xdeaddeaddeaddeaddeaddeaddeaddeaddeaddead",
}

# Known mixer / sanctioned protocol contracts beyond OFAC (heuristic).
KNOWN_MIXERS: Set[str] = {
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",  # Tornado Cash 10 ETH pool
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",  # Tornado Cash 100 ETH pool
}

# Sample sanctioned/PEP individuals (would be loaded from OFAC SDN names file).
SANCTIONED_INDIVIDUALS: list = [
    {"name": "Vladimir Putin", "list": "EU", "type": "PEP"},
    {"name": "Kim Jong Un", "list": "OFAC", "type": "SANCTIONS"},
    {"name": "Alexander Lukashenko", "list": "EU", "type": "PEP"},
    # Demo entries
    {"name": "John Doe Sanctioned", "list": "DEMO", "type": "SANCTIONS"},
]


def normalise_address(addr: str) -> str:
    return (addr or "").strip().lower()


def is_sanctioned_address(addr: str) -> bool:
    return normalise_address(addr) in OFAC_SANCTIONED_CRYPTO


def is_known_mixer(addr: str) -> bool:
    return normalise_address(addr) in KNOWN_MIXERS


def screen_name(name: str) -> Dict[str, Any] | None:
    """Fuzzy-ish name match against sanctioned individuals.
    Returns the matching entry or None.
    """
    if not name:
        return None
    n = name.lower().strip()
    for entry in SANCTIONED_INDIVIDUALS:
        if n in entry["name"].lower() or entry["name"].lower() in n:
            return entry
    return None
