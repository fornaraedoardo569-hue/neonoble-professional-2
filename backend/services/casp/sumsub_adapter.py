"""Sumsub KYC adapter.

Implementation modes:
  - MOCK (default): generates deterministic applicants, simulates the review
    flow, marks every test applicant as APPROVED after 5 seconds.
  - LIVE: hits https://api.sumsub.com with HMAC signed requests using the
    SUMSUB_APP_TOKEN / SUMSUB_SECRET_KEY environment variables.

Switch via SUMSUB_LIVE=true in backend .env once the partner contract is
active and the production token has been issued.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Optional, Dict, Any

import httpx

from .base import KycProvider

logger = logging.getLogger(__name__)


class SumsubAdapter(KycProvider):
    name = "sumsub"
    BASE_URL = "https://api.sumsub.com"

    def __init__(self) -> None:
        self.app_token = os.environ.get("SUMSUB_APP_TOKEN", "")
        self.secret_key = os.environ.get("SUMSUB_SECRET_KEY", "")
        self.applicant_level = os.environ.get("SUMSUB_APPLICANT_LEVEL", "basic-kyc-level")
        self.webhook_secret = os.environ.get("SUMSUB_WEBHOOK_SECRET", "")
        self.is_live = (
            os.environ.get("SUMSUB_LIVE", "false").lower() == "true"
            and bool(self.app_token)
            and bool(self.secret_key)
        )
        if self.is_live:
            logger.info("SumsubAdapter initialised in LIVE mode")
        else:
            logger.info("SumsubAdapter initialised in MOCK mode")

    # ── public api ──────────────────────────────────────────────────────────

    async def create_applicant(self, user_id: str, email: str, **kwargs) -> Dict[str, Any]:
        if not self.is_live:
            return self._mock_applicant(user_id, email)

        method = "POST"
        path = f"/resources/applicants?levelName={self.applicant_level}"
        body = {
            "externalUserId": user_id,
            "email": email,
            "type": kwargs.get("type", "individual"),
        }
        headers = self._signed_headers(method, path, body)

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.BASE_URL}{path}", json=body, headers=headers)
            r.raise_for_status()
            data = r.json()

        token_payload = await self._fetch_access_token(data["id"], user_id)
        return {
            "provider_applicant_id": data["id"],
            "access_token": token_payload["token"],
            "expires_in": token_payload.get("expiresIn"),
            "raw": data,
        }

    async def get_applicant_status(self, applicant_id: str) -> Dict[str, Any]:
        if not self.is_live:
            return self._mock_status(applicant_id)

        method = "GET"
        path = f"/resources/applicants/{applicant_id}/status"
        headers = self._signed_headers(method, path, body=None)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.BASE_URL}{path}", headers=headers)
            r.raise_for_status()
            return r.json()

    async def verify_webhook(self, body: bytes, signature: str) -> bool:
        if not self.webhook_secret or not signature:
            # MOCK acceptance
            return not self.is_live
        digest = hmac.new(self.webhook_secret.encode(), body, hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, signature)

    async def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "type": payload.get("type"),
            "applicant_id": payload.get("applicantId"),
            "review_status": payload.get("reviewStatus"),
            "review_result": payload.get("reviewResult", {}),
            "external_user_id": payload.get("externalUserId"),
        }

    # ── helpers ─────────────────────────────────────────────────────────────

    async def _fetch_access_token(self, applicant_id: str, user_id: str) -> Dict[str, Any]:
        method = "POST"
        path = (
            f"/resources/accessTokens?userId={user_id}"
            f"&levelName={self.applicant_level}&ttlInSecs=1800"
        )
        headers = self._signed_headers(method, path, body=None)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self.BASE_URL}{path}", headers=headers)
            r.raise_for_status()
            return r.json()

    def _signed_headers(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> Dict[str, str]:
        ts = str(int(time.time()))
        body_str = json.dumps(body) if body is not None else ""
        msg = f"{ts}{method}{path}{body_str}".encode()
        sig = hmac.new(self.secret_key.encode(), msg, hashlib.sha256).hexdigest()
        return {
            "X-App-Token": self.app_token,
            "X-App-Access-Sig": sig,
            "X-App-Access-Ts": ts,
            "Content-Type": "application/json",
        }

    def _mock_applicant(self, user_id: str, email: str) -> Dict[str, Any]:
        applicant_id = f"mock_{uuid.uuid4().hex[:12]}"
        logger.info(f"[mock-sumsub] applicant {applicant_id} created for {email}")
        return {
            "provider_applicant_id": applicant_id,
            "access_token": f"mock_token_{applicant_id}",
            "expires_in": 1800,
            "raw": {"id": applicant_id, "email": email, "externalUserId": user_id, "mock": True},
        }

    def _mock_status(self, applicant_id: str) -> Dict[str, Any]:
        return {
            "id": applicant_id,
            "reviewStatus": "completed",
            "reviewResult": {"reviewAnswer": "GREEN"},
            "mock": True,
        }
