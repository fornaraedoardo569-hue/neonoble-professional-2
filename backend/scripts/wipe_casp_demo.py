"""Wipe all DEMO data from the CASP collections — leaves admin users
intact so you can still log in.

Run **once** before going live in production with real customers and real
peer VASPs. Idempotent.

Usage:
    cd /app/backend && python scripts/wipe_casp_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from motor.motor_asyncio import AsyncIOMotorClient


DEMO_EMAIL_PATTERNS = [
    r"^client_\d+@neonoble-demo\.example\.com$",
    r"^institutional@bigcorp\.example\.com$",
]
DEMO_VASP_DIDS = [
    "did:web:bigexchange.example",
    "did:web:cryptoexch.example",
    "did:web:safecustody.example",
]


async def main() -> None:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ.get("DB_NAME", "neonoble_ramp")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("⚠️  This will REMOVE all demo data from CASP collections.")
    print("    Admin users (casp-*@neonoble.example.com) will be preserved.")
    print()

    # 1) Remove demo customers (users + their KYC/KYB/risk records)
    demo_user_ids = []
    async for u in db.users.find(
        {"email": {"$regex": "|".join(DEMO_EMAIL_PATTERNS), "$options": "i"}},
        {"_id": 0, "id": 1, "email": 1},
    ):
        demo_user_ids.append(u["id"])
    print(f"→ Found {len(demo_user_ids)} demo users — removing…")
    if demo_user_ids:
        await db.users.delete_many({"id": {"$in": demo_user_ids}})
        await db.casp_kyc.delete_many({"user_id": {"$in": demo_user_ids}})
        await db.casp_kyb.delete_many({"user_id": {"$in": demo_user_ids}})
        await db.casp_risk_rating.delete_many({"user_id": {"$in": demo_user_ids}})
        await db.casp_complaints.delete_many({"user_id": {"$in": demo_user_ids}})

    # 2) Remove demo AML alerts (those seeded with DEMO_ prefix)
    r = await db.casp_aml_alerts.delete_many({"rule_id": {"$regex": "^DEMO_"}})
    print(f"→ Removed {r.deleted_count} DEMO AML alerts")

    # 3) Remove demo wallets (those addresses start with `0xdemo`)
    r = await db.casp_wallets.delete_many({"address": {"$regex": "^0xdemo"}})
    print(f"→ Removed {r.deleted_count} DEMO wallets")

    # 4) Remove demo OTC quotes (references created by seed start with OTC- and year-prefixed)
    # Keep this loose so live OTC quotes survive; we only remove ones with no real client.
    r = await db.casp_otc_b2b.delete_many({"client_user_id": {"$in": demo_user_ids}})
    print(f"→ Removed {r.deleted_count} demo OTC quotes")

    # 5) Remove demo peer VASPs and any TRP inbox entries from them
    r = await db.casp_vasp_directory.delete_many({"did": {"$in": DEMO_VASP_DIDS}})
    print(f"→ Removed {r.deleted_count} demo peer VASPs")
    r = await db.casp_trp_inbox.delete_many({"peer_did": {"$in": DEMO_VASP_DIDS}})
    print(f"→ Removed {r.deleted_count} demo TRP inbox messages")

    # 6) Remove demo asset disclosures (the seed inserts 4 generic ones)
    r = await db.casp_disclosures.delete_many({})
    print(f"→ Removed {r.deleted_count} demo disclosures (re-author with real whitepapers)")

    # 7) Remove demo conflicts of interest
    r = await db.casp_conflicts.delete_many({"party": {"$regex": "demo"}})
    print(f"→ Removed {r.deleted_count} demo conflicts")

    # 8) Reset capital snapshot to a single 'unknown' starting point
    await db.casp_capital_snapshots.delete_many({})
    print("→ Cleared capital snapshots — record your real own-funds with /admin/reporting")

    # 9) Reset Proof-of-Reserves snapshots
    await db.casp_proof_of_reserves.delete_many({})
    print("→ Cleared PoR snapshots — generate a new one from /admin/treasury once wallets are real")

    # 10) Keep audit log: regulators want continuity.
    print("→ Audit log preserved (regulators require continuity)")

    print()
    print("=" * 60)
    print("✅ CASP demo data wiped. Now configure real data via /admin.")
    print("   Admin login still works:")
    print("   casp-admin@neonoble.example.com / CaspAdmin!2026")
    print("   (Change this password immediately!)")
    print("=" * 60)
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
