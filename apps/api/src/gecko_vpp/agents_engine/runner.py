"""Orchestrator — classify → fetch → render → log.

The FastAPI router calls `handle_query` and serialises the returned dict.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from gecko_vpp.agents_engine.classifier import FALLBACK_INTENT, classify
from gecko_vpp.agents_engine.fallback import render_fallback
from gecko_vpp.agents_engine.intents import get_intent
from gecko_vpp.agents_engine.personas import ALLOWED_PERSONAS
from gecko_vpp.models.agents import QueryLog

log = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    answer: str
    intent: str
    confidence: float
    evidence: list[dict[str, Any]]
    persona: str
    duration_ms: int
    matched_pattern: str
    normalised_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "persona": self.persona,
            "duration_ms": self.duration_ms,
        }


async def handle_query(
    session: AsyncSession,
    *,
    tenant_id: str,
    persona: str,
    user_text: str,
) -> AgentResponse:
    """Full pipeline. Always returns an AgentResponse; never raises on
    intent-handler errors (degrades to fallback + logs).
    """
    t0 = time.monotonic()
    if persona not in ALLOWED_PERSONAS:
        # Caller should have validated; defensive fallback here.
        persona = "dispatcher_analyst"

    cls = classify(user_text or "", persona)
    answer: str
    evidence: list[dict[str, Any]] = []

    if cls.intent == FALLBACK_INTENT:
        answer = render_fallback(persona)
    else:
        spec = get_intent(cls.intent)
        if spec is None:
            answer = render_fallback(persona)
        else:
            try:
                slots = await spec["fetch_slots"](session, tenant_id=tenant_id)
                evidence = list(slots.get("_evidence", []) or [])
                answer = spec["render"](slots, persona)
            except Exception:
                log.exception("agent_intent_failed intent=%s", cls.intent)
                answer = render_fallback(persona)
                evidence = []

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Write query_log (best effort — don't surface DB errors).
    try:
        log_row = QueryLog(
            tenant_id=UUID(tenant_id),
            persona=persona,
            user_text=user_text or "(empty)",
            classified_intent=cls.intent,
            confidence=Decimal(str(cls.confidence)),
            response_text=answer,
            evidence=evidence,
            duration_ms=duration_ms,
        )
        session.add(log_row)
        await session.flush()
    except Exception:
        log.exception("agent_query_log_failed")

    return AgentResponse(
        answer=answer,
        intent=cls.intent,
        confidence=cls.confidence,
        evidence=evidence,
        persona=persona,
        duration_ms=duration_ms,
        matched_pattern=cls.matched_pattern,
        normalised_text=cls.normalised_text,
    )
