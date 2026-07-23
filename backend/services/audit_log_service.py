"""Audit log service — produces hash-chained immutable entries (WORM).

Each entry hashes (sequence + actor + action + entity_id + payload + prev_hash)
so any tampering is detectable: a verifier can replay the chain and compare
hashes. Suitable as evidence of integrity for CONSOB / Banca d'Italia audits.

We deliberately do NOT delete or update entries. The collection has a
unique index on `sequence` to guarantee monotonicity.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def _canonical(obj: Any) -> str:
    """Deterministic JSON encoding so the hash is stable across processes."""
    def default(o):
        if isinstance(o, datetime):
            return o.astimezone(timezone.utc).isoformat()
        return str(o)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=default)


class AuditLogService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.casp_audit_log

    async def initialize(self) -> None:
        await self.collection.create_index("sequence", unique=True)
        await self.collection.create_index("entity_id")
        await self.collection.create_index("actor_id")
        await self.collection.create_index("created_at")

    async def append(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append a new entry and return the persisted document (minus _id)."""
        last = await self.collection.find_one(
            {}, sort=[("sequence", -1)], projection={"_id": 0, "sequence": 1, "hash": 1}
        )
        sequence = (last["sequence"] + 1) if last else 1
        prev_hash = last["hash"] if last else "0" * 64

        entry = {
            "sequence": sequence,
            "actor_id": actor_id or "system",
            "actor_email": actor_email,
            "actor_role": actor_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload": payload or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "prev_hash": prev_hash,
            "created_at": datetime.now(timezone.utc),
        }
        # Compute the chained hash from a canonical encoding.
        material = _canonical({k: entry[k] for k in (
            "sequence", "actor_id", "action", "entity_type", "entity_id", "payload", "prev_hash"
        )})
        entry["hash"] = hashlib.sha256(material.encode()).hexdigest()

        await self.collection.insert_one(entry)
        return {k: v for k, v in entry.items() if k != "_id"}

    async def list(self, limit: int = 100, skip: int = 0,
                   entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if entity_id:
            q["entity_id"] = entity_id
        cursor = self.collection.find(q, {"_id": 0}).sort("sequence", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def verify_chain(self, limit: int = 1000) -> Dict[str, Any]:
        """Walk the chain forward and verify every hash. Returns a summary."""
        cursor = self.collection.find({}, {"_id": 0}).sort("sequence", 1).limit(limit)
        entries = await cursor.to_list(length=limit)
        if not entries:
            return {"verified": True, "checked": 0, "first_break": None}

        prev_hash = "0" * 64
        for e in entries:
            if e["prev_hash"] != prev_hash:
                return {"verified": False, "checked": e["sequence"],
                        "first_break": e["sequence"], "reason": "prev_hash_mismatch"}
            material = _canonical({k: e[k] for k in (
                "sequence", "actor_id", "action", "entity_type", "entity_id", "payload", "prev_hash"
            )})
            expected = hashlib.sha256(material.encode()).hexdigest()
            if expected != e["hash"]:
                return {"verified": False, "checked": e["sequence"],
                        "first_break": e["sequence"], "reason": "hash_mismatch"}
            prev_hash = e["hash"]
        return {"verified": True, "checked": len(entries), "first_break": None}
