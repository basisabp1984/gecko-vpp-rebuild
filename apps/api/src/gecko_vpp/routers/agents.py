"""Agents router — deterministic classifier + DB-evidence-backed answers.

Replaces the Stage 4d stub. Engine lives in `gecko_vpp.agents_engine.*`.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine import handle_query
from gecko_vpp.agents_engine.personas import ALLOWED_PERSONAS, PERSONAS
from gecko_vpp.common.envelope import build_success
from gecko_vpp.common.errors import ValidationFailed
from gecko_vpp.config import get_settings
from gecko_vpp.deps import get_session, get_tenant_id
from gecko_vpp.schemas.agents import AgentQueryIn, AgentQueryOut, VoiceSessionOut

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post(
    "/{persona}/query",
    operation_id="agents.persona.query",
)
async def agent_query(
    persona: Annotated[str, Path()],
    body: AgentQueryIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if persona not in ALLOWED_PERSONAS:
        raise ValidationFailed(
            "Unknown persona",
            {"allowed": sorted(ALLOWED_PERSONAS), "given": persona},
        )
    user_text = body.question or body.text or ""

    result = await handle_query(
        session,
        tenant_id=tenant_id,
        persona=persona,
        user_text=user_text,
    )

    payload = AgentQueryOut(
        answer=result.answer,
        intent=result.intent,
        confidence=result.confidence,
        evidence=result.evidence,
        persona=result.persona,
        duration_ms=result.duration_ms,
    )
    return build_success(payload.model_dump(mode="json"), tenant_id=tenant_id)


@router.get("/personas", operation_id="agents.personas.list")
async def list_personas() -> dict[str, Any]:
    """Return persona registry for the frontend AgentChat (display_name,
    allowed_intents, fallback_sample_questions).
    """
    data = {
        code: {
            "code": code,
            "display_name": cfg["display_name"],
            "greeting": cfg["greeting"],
            "voice": cfg["voice"],
            "allowed_intents": list(cfg["allowed_intents"]),
            "fallback_sample_questions": list(cfg["fallback_sample_questions"]),
        }
        for code, cfg in PERSONAS.items()
    }
    return build_success(data)


@router.get("/voice/session", operation_id="agents.voice.session")
async def voice_session() -> dict[str, Any]:
    settings = get_settings()
    provider = settings.voice_provider or "stub"
    has_key = bool(settings.openai_api_key)
    if provider == "openai-realtime" and not has_key:
        provider = "stub"

    canned = [
        {"intent": "production_today", "trigger": "що сьогодні з виробництвом"},
        {"intent": "battery_schedule", "trigger": "коли заряджати батарею"},
        {"intent": "imbalance_explain", "trigger": "поясни небаланс"},
        {"intent": "arbitrage_window", "trigger": "коли арбітражне вікно"},
        {"intent": "savings_summary", "trigger": "скільки зекономили"},
    ]

    if provider == "stub":
        out = VoiceSessionOut(
            provider="stub",
            session_token=None,
            websocket_url=None,
            canned_scenarios=canned,
        )
    else:
        out = VoiceSessionOut(
            provider=provider,
            session_token="ephemeral-key-placeholder",
            websocket_url="wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
            canned_scenarios=canned,
        )
    return build_success(out.model_dump(mode="json"))
