"""
One-shot migration: normalise stored user emails to lowercase.

Background: before the case-insensitive fix, users registering with any
uppercase character in the email *local part* could end up with mixed-case
documents in MongoDB. Login lookups (now lowercased) would then fail.

This script lowercases every existing user.email and merges duplicates
(keeping the oldest document, deleting the rest). It's idempotent.

Usage:
    cd /app/backend && python -m scripts.normalise_user_emails
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow `python -m scripts.normalise_user_emails` from /app/backend
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def main() -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("MONGO_URL / DB_NAME not set", file=sys.stderr)
        return 1

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    users = db.users

    cursor = users.find({}, {"_id": 1, "id": 1, "email": 1, "created_at": 1})
    fixed = 0
    deleted_duplicates = 0
    seen_by_lower = {}

    async for doc in cursor:
        original = doc.get("email") or ""
        lower = original.strip().lower()
        if not lower:
            continue
        if lower in seen_by_lower:
            # Duplicate detected — keep the older document, delete this one
            existing = seen_by_lower[lower]
            keep, drop = sorted(
                (existing, doc),
                key=lambda d: d.get("created_at") or "9999",
            )
            await users.delete_one({"_id": drop["_id"]})
            seen_by_lower[lower] = keep
            deleted_duplicates += 1
            print(f"  deleted duplicate: {drop.get('email')} (kept {keep.get('email')})")
            continue
        seen_by_lower[lower] = doc
        if original != lower:
            await users.update_one({"_id": doc["_id"]}, {"$set": {"email": lower}})
            fixed += 1
            print(f"  normalised: {original} -> {lower}")

    print(f"\nDone. Normalised {fixed} emails. Deleted {deleted_duplicates} duplicate(s).")

    # Re-create the unique index on email (drop & recreate to be safe)
    try:
        await users.drop_index("email_1")
    except Exception:
        pass
    await users.create_index("email", unique=True, name="email_1")
    print("Unique index on `email` ensured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
