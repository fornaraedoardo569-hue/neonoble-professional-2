"""CASP RBAC dependency.

Authenticated admin users carry a list of CASP roles stored in the
`casp_admin_users` collection. The dependency below checks that the
current user owns at least one of the required roles.

The base UserRole.ADMIN bypasses CASP-role checks (super-admin).
"""

from __future__ import annotations

from typing import Iterable, List, Optional
from fastapi import Depends, HTTPException, Request

from middleware.auth import get_current_user

# Filled in by server.py at startup so we can reach the casp_admin_users collection
_db = None


def bind_db(db) -> None:
    global _db
    _db = db


async def _fetch_casp_roles(user_id: str) -> List[str]:
    if _db is None:
        return []
    doc = await _db.casp_admin_users.find_one({"user_id": user_id, "is_active": True}, {"_id": 0, "casp_roles": 1})
    return doc.get("casp_roles", []) if doc else []


def require_casp_roles(*allowed: str):
    """FastAPI dependency factory — enforces CASP role membership."""
    allowed_set = set(allowed)

    async def _dep(request: Request, user: dict = Depends(get_current_user)) -> dict:
        # Super-admin shortcut
        if user.get("role") == "ADMIN":
            return {**user, "casp_roles": ["ADMIN"]}

        roles = await _fetch_casp_roles(user["user_id"])
        if not roles:
            raise HTTPException(status_code=403, detail="Not a CASP admin user")
        if allowed_set and not allowed_set.intersection(set(roles)):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of CASP roles: {sorted(allowed_set)}",
            )
        return {**user, "casp_roles": roles}

    return _dep


# Convenience pre-built dependencies (most common combinations)
require_compliance = require_casp_roles("ADMIN", "MLRO", "COMPLIANCE_OFFICER")
require_mlro = require_casp_roles("ADMIN", "MLRO")
require_risk = require_casp_roles("ADMIN", "RISK_OFFICER", "MLRO")
require_treasury = require_casp_roles("ADMIN", "TREASURY_OFFICER")
require_otc_trader = require_casp_roles("ADMIN", "OTC_TRADER")
require_otc_approver = require_casp_roles("ADMIN", "MLRO", "RISK_OFFICER")
require_any_admin = require_casp_roles(
    "ADMIN", "MLRO", "COMPLIANCE_OFFICER", "RISK_OFFICER",
    "TREASURY_OFFICER", "OTC_TRADER", "AUDITOR",
)
