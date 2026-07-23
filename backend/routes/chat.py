"""AI Assistant routes — Claude (claude-sonnet-4-6) via Emergent LLM key.

Three assistant contexts, each with its own system prompt and role gate:
  * dashboard — retail users (any authenticated role)
  * devportal — DEVELOPER / ADMIN
  * admin     — ADMIN only (CASP back-office compliance copilot)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from middleware.auth import get_current_user

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])

_db = None


def set_db(db) -> None:
    global _db
    _db = db


MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"
HISTORY_LIMIT = 30

_COMMON = (
    "You are NoNo, the AI assistant of NeoNoble Ramp, the on/off-ramp platform by "
    "NeoNoble Technology Incorporation Limited for the NeoNoble Token ($NENO), a BEP-20 "
    "token on Binance Smart Chain (contract 0xeF3F5C1892A8d7A3304E4A15959E124402d69974, "
    "fixed OTC price €10,000). Always reply in the same language the user writes in "
    "(e.g. Italian if they write Italian). Be concise, accurate and friendly. "
    "If you don't know something specific to the platform, say so instead of inventing."
)

CONTEXTS = {
    "dashboard": {
        "roles": None,
        "system": _COMMON + (
            " You assist retail customers on their Dashboard. You can help with: buying/selling "
            "NENO via the Start Trading card (Transak widget, EUR default), the enterprise OTC desk "
            "(fixed €10,000, Stripe SEPA settlement), completing KYC at /onboarding (ID document + "
            "selfie, reviewed by compliance — transactions are blocked until KYC is APPROVED), "
            "60-minute locked quotes, and the non-custodial PancakeSwap USDC↔NENO swap at /transak. "
            "Never provide financial or investment advice — remind users crypto is high risk."
        ),
    },
    "devportal": {
        "roles": {"DEVELOPER", "ADMIN"},
        "system": _COMMON + (
            " You assist developers in the Developer Portal. You can help with: creating platform "
            "API keys, HMAC-SHA256 authentication (headers X-API-KEY, X-TIMESTAMP, X-SIGNATURE where "
            "signature = HMAC-SHA256(timestamp + bodyJson, apiSecret)), the public Ramp API "
            "(POST /api/v1/onramp/quote, /onramp/execute, /offramp/quote, /offramp/execute), the "
            "Transak widget endpoint POST /api/transak/widget-url (for NENO the backend auto-injects "
            "the BSC contract and forces network=bsc + EUR), webhooks, and rate limits. "
            "Provide working code snippets when useful."
        ),
    },
    "admin": {
        "roles": {"ADMIN"},
        "system": _COMMON + (
            " You are the compliance copilot of the CASP back-office (MiCAR). You assist internal "
            "operators (MLRO, compliance officers) with the 7 operational blocks: 1) KYC/KYB, risk "
            "scoring and sanctions screening; 2) AML transaction monitoring, Travel Rule (IVMS-101) "
            "and SAR drafting; 3) custody, reconciliation and proof-of-reserves; 4) B2B OTC desk with "
            "4-eye approval above €50k; 5) regulatory reporting and capital adequacy; 6) customer "
            "protection, complaints (15-day SLA) and asset disclosures; 7) RBAC, DORA operational "
            "incidents and conflicts of interest. Reference MiCAR (EU 2023/1114), AMLD5/6 and the "
            "EBA/ESMA guidelines where relevant, but always clarify you provide operational guidance, "
            "not legal advice."
        ),
    },
}


class CreateSessionReq(BaseModel):
    context: str = Field(pattern="^(dashboard|devportal|admin)$")


class StreamReq(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


def _check_context(context: str, user: dict) -> dict:
    cfg = CONTEXTS.get(context)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown assistant context")
    if cfg["roles"] and user["role"] not in cfg["roles"]:
        raise HTTPException(status_code=403, detail="Insufficient role for this assistant")
    return cfg


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/sessions")
async def create_session(body: CreateSessionReq, user: dict = Depends(get_current_user)):
    _check_context(body.context, user)
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "context": body.context,
        "title": "New conversation",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await _db.chat_sessions.insert_one({**session})
    return session


@router.get("/sessions")
async def list_sessions(context: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"user_id": user["user_id"]}
    if context:
        q["context"] = context
    cursor = _db.chat_sessions.find(q, {"_id": 0}).sort("updated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, user: dict = Depends(get_current_user)):
    session = await _db.chat_sessions.find_one({"id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    cursor = _db.chat_messages.find({"session_id": session_id}, {"_id": 0}).sort("created_at", 1)
    return await cursor.to_list(200)


@router.post("/sessions/{session_id}/stream")
async def stream_reply(session_id: str, body: StreamReq, user: dict = Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

    session = await _db.chat_sessions.find_one({"id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    cfg = _check_context(session["context"], user)

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

    history_cursor = _db.chat_messages.find(
        {"session_id": session_id}, {"_id": 0, "role": 1, "content": 1}
    ).sort("created_at", 1)
    history = await history_cursor.to_list(500)
    history = history[-HISTORY_LIMIT:]
    is_first = len(history) == 0

    await _db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": "user",
        "content": body.message,
        "created_at": _now(),
    })

    initial = [{"role": "system", "content": cfg["system"]}]
    initial += [{"role": m["role"], "content": m["content"]} for m in history]

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=cfg["system"],
        initial_messages=initial,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)

    async def event_generator():
        full_text = ""
        try:
            async for ev in chat.stream_message(UserMessage(text=body.message)):
                if isinstance(ev, TextDelta):
                    full_text += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"Assistant stream error: {e}")
            yield f"data: {json.dumps({'error': 'The assistant is temporarily unavailable. Please try again.'})}\n\n"
            return
        await _db.chat_messages.insert_one({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "assistant",
            "content": full_text,
            "created_at": _now(),
        })
        update = {"updated_at": _now()}
        if is_first:
            update["title"] = body.message[:60]
        await _db.chat_sessions.update_one({"id": session_id}, {"$set": update})
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
